import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from catalog_loader import list_profiles
from core.env_loader import load_env
from core.geometry_engine import parse_add_structural_element
from core.spatial_context import format_project_context
from schemas.chat import ChatMessage
from schemas.elements import ProjectElementMm
from schemas.project import ProjectState
from tools.element_tool import ELEMENT_TOOLS

load_env()

MODEL = "gpt-4o-mini"
MAX_TURNS = 5

_CATALOG_SUMMARY = ", ".join(
    f"{p['profile_name']} (h={p['h_mm']} b={p['b_mm']} tw={p['tw_mm']} tf={p['tf_mm']} mm)"
    for p in list_profiles()
)

BASE_SYSTEM_PROMPT = f"""You are Steelera AI for parametric structural steel design.

When the user asks to add or build members, call add_structural_element once per member.

Required on every call:
- shape_type, length, width, position, profile_name, axis, anchor_element_id, anchor_point

Section definition:
1) **Catalog** — profile_name = IPE200 | IPE300 | HEA200 (shape_type I-beam). Set width to {{value:0, unit:"mm"}}.
   Available: {_CATALOG_SUMMARY}
2) **Parametric** — profile_name = NONE and set width.

Spatial anchoring (relative placement):
- When placing relative to existing steel, set anchor_element_id to the target id from CURRENT MODEL
  and anchor_point to TOP | BOTTOM | START | END | CENTER. Set position to {{0,0,0}} (ignored).
- CENTER = midpoint of target member (column on center of beam). END = far tip only.
- TOP = top face (e.g. beam on column top). BOTTOM = base. START/END = along member length axis.
- When anchor_element_id is NONE, use absolute position coordinates.

Axis: y = vertical column, x = horizontal beam along X, z = along Z.

Units: m, mm, ft, in, or auto (value<20 => meters, value>=20 => mm).

When adding to an existing model, APPEND new members — do not replace unless the user asks to rebuild.
Do not invent geometry in prose only—use the tool for every member.
For general questions without structure, respond without tools.
"""


def build_system_prompt(project_elements: list[ProjectElementMm]) -> str:
    """Base prompt + readable inventory of already-built members."""
    context = format_project_context(project_elements)
    return f"{BASE_SYSTEM_PROMPT}\n\n---\n{context}"


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _execute_add_element(
    arguments: str,
    elements: list[ProjectElementMm],
    replace_next: bool,
) -> tuple[list[ProjectElementMm], dict[str, Any], bool]:
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e

    working = [] if replace_next else list(elements)
    index = len(working)
    element = parse_add_structural_element(args, index, existing_elements=working)
    working.append(element)

    summary: dict[str, Any] = {
        "success": True,
        "element_id": element.id,
        "total_elements": len(working),
        "length_mm": element.length_mm,
        "position_mm": element.position_mm,
        "section_source": element.section_source,
    }
    if element.anchor_element_id:
        summary["anchored_to"] = element.anchor_element_id
        summary["anchor_point"] = element.anchor_point
    if element.profile_name and element.section_mm:
        summary["profile_name"] = element.profile_name
        summary["section_mm"] = element.section_mm.model_dump()
    else:
        summary["width_mm"] = element.width_mm

    return working, summary, False


def run_chat_turn(
    messages: list[ChatMessage],
    project_state: ProjectState,
    *,
    spatial_context: str | None = None,
) -> tuple[str, list[str], ProjectState]:
    """GPT-4o-mini tool loop with spatial context from existing projectElements."""
    statuses: list[str] = ["Parsing request..."]
    client = _client()
    statuses.append("Calling Steelera AI (gpt-4o-mini)...")

    elements: list[ProjectElementMm] = list(project_state.projectElements)
    system_content = spatial_context or build_system_prompt(elements)

    openai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        *_messages_to_openai(messages),
    ]

    # Append mode when model already has members (supports "add beam on column")
    replace_next = len(elements) == 0
    assistant_content = ""

    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            tools=ELEMENT_TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            assistant_content = msg.content or ""
            break

        openai_messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        for tc in msg.tool_calls:
            name = tc.function.name
            if name == "add_structural_element":
                statuses.append("Adding structural element...")
                try:
                    elements, summary, replace_next = _execute_add_element(
                        tc.function.arguments or "{}",
                        elements,
                        replace_next,
                    )
                    if summary.get("anchored_to"):
                        statuses.append(
                            f"Anchored to {summary['anchored_to']} ({summary.get('anchor_point')})..."
                        )
                    elif summary.get("profile_name"):
                        statuses.append(
                            f"Loaded catalog {summary['profile_name']}..."
                        )
                except (ValueError, ValidationError) as e:
                    summary = {"success": False, "error": str(e)}
            else:
                summary = {"success": False, "error": f"Unknown tool: {name}"}

            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(summary),
                }
            )

        statuses.append("Building millimeter geometry...")
    else:
        assistant_content = assistant_content or (
            "Structural update complete. Check the 3D viewport."
        )

    if not assistant_content:
        followup = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
        )
        assistant_content = followup.choices[0].message.content or (
            "Members were added with spatial context applied."
        )

    statuses.append("Rendering structure...")
    return assistant_content, statuses, ProjectState(
        version=3, projectElements=elements
    )

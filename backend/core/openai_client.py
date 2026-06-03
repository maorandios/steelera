import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from catalog_loader import list_profiles
from core.env_loader import load_env
from core.geometry_engine import apply_macro_action, parse_add_structural_element
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

Macro actions (duplicate / array / delete):
- When the user asks to copy, duplicate, array, multiply, or delete a member, call apply_macro_action — NOT multiple add_structural_element calls.
- ARRAY: target_element_id, count (copies to create, excluding original), spacing {{value, unit}}, axis = world offset direction (right/+X = X, up/+Y = Y, forward/+Z = Z).
- DELETE: target_element_id, action_type DELETE (set count/spacing/axis to null).
- If the user selected an element, use that id as target_element_id when they say "this" or "it".

Units: m, mm, ft, in, or auto (value<20 => meters, value>=20 => mm).

When adding to an existing model, APPEND new members — do not replace unless the user asks to rebuild.
Do not invent geometry in prose only—use the tool for every structural change.
NEVER claim members were added, duplicated, or deleted unless a tool call returned success:true.
For general questions without structure, respond without tools.
"""


def _selection_context(target_element_id: str | None) -> str:
    if not target_element_id:
        return ""
    return (
        f"\n\n---\n"
        f"The user has currently selected element '{target_element_id}'. "
        f"If they ask to copy, array, multiply, or delete 'this' or 'it', "
        f"call apply_macro_action with this target_element_id."
    )


def build_system_prompt(
    project_elements: list[ProjectElementMm],
    *,
    target_element_id: str | None = None,
) -> str:
    """Base prompt + readable inventory of already-built members."""
    context = format_project_context(project_elements)
    selection = _selection_context(target_element_id)
    return f"{BASE_SYSTEM_PROMPT}\n\n---\n{context}{selection}"


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


def _is_macro_request(text: str) -> bool:
    t = text.lower()
    return any(
        word in t
        for word in ("duplicate", "copy", "array", "multiply", "clone", "delete")
    )


def _execute_macro_action(
    arguments: str,
    elements: list[ProjectElementMm],
    *,
    fallback_target_id: str | None = None,
) -> tuple[list[ProjectElementMm], dict[str, Any]]:
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e

    if fallback_target_id:
        target = str(args.get("target_element_id", "")).strip()
        known = {element.id for element in elements}
        if target not in known:
            args["target_element_id"] = fallback_target_id

    return apply_macro_action(args, elements)


def run_chat_turn(
    messages: list[ChatMessage],
    project_state: ProjectState,
    *,
    spatial_context: str | None = None,
    target_element_id: str | None = None,
) -> tuple[str, list[str], ProjectState]:
    """GPT-4o-mini tool loop with spatial context from existing projectElements."""
    statuses: list[str] = ["Parsing request..."]
    client = _client()
    statuses.append("Calling Steelera AI (gpt-4o-mini)...")

    elements: list[ProjectElementMm] = list(project_state.projectElements)
    initial_count = len(elements)
    system_content = spatial_context or build_system_prompt(
        elements,
        target_element_id=target_element_id,
    )

    openai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        *_messages_to_openai(messages),
    ]

    last_user_text = messages[-1].content if messages else ""
    force_macro = bool(elements and _is_macro_request(last_user_text))

    # Append mode when model already has members (supports "add beam on column")
    replace_next = len(elements) == 0
    assistant_content = ""
    tools_used = False

    for turn in range(MAX_TURNS):
        tool_choice: Any = "auto"
        if force_macro and turn == 0:
            tool_choice = {"type": "function", "function": {"name": "apply_macro_action"}}

        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            tools=ELEMENT_TOOLS,
            tool_choice=tool_choice,
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
                    tools_used = tools_used or summary.get("success") is True
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
            elif name == "apply_macro_action":
                statuses.append("Applying macro action...")
                try:
                    elements, summary = _execute_macro_action(
                        tc.function.arguments or "{}",
                        elements,
                        fallback_target_id=target_element_id,
                    )
                    tools_used = tools_used or summary.get("success") is True
                    if summary.get("action") == "ARRAY":
                        statuses.append(
                            f"Arrayed {summary.get('source_id')} → "
                            f"{summary.get('count')} copies along {summary.get('axis')} "
                            f"at {summary.get('spacing_mm')} mm..."
                        )
                    elif summary.get("action") == "DELETE":
                        statuses.append(
                            f"Deleted {summary.get('deleted_id')}..."
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

    if force_macro and not tools_used:
        assistant_content = (
            "I couldn't apply that change to the selected member. "
            "Please try again with the member selected in the viewport."
        )
    elif not assistant_content:
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

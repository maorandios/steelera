import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env", override=True)
from pydantic import ValidationError

from core.structural_engine import generate_structural_elements_from_dicts
from schemas.chat import ChatMessage
from schemas.project import ProjectState
from tools.structural_tool import STRUCTURAL_TOOLS

MODEL = "gpt-4o-mini"
MAX_TURNS = 3

SYSTEM_PROMPT = """You are Steelera AI, an assistant for parametric structural steel design.

When the user asks to build, add, or replace structural members, you MUST call
generate_structural_elements with an array of member objects. Each object needs:
shape_type (I-beam | C-channel | Box | Pipe), height, width, thickness, length,
position {x, y, z}, and axis (x | y | z) for the direction the member runs in meters.

Rules:
- Convert feet to meters (1 ft = 0.3048 m).
- position is the member start point (min corner of the bounding box).
- length is along the local X axis from that start point.
- For sheds/frames, decompose into columns (I-beam or Box), rafters (I-beam),
  purlins (C-channel), and bracing (Box/Pipe) with realistic section sizes.
- Use typical steel sizes (e.g. 0.2–0.4 m depth) unless the user specifies otherwise.
- Do not invent geometry only in prose—use the tool for all structural generation.
- For general questions without structure to generate, respond without calling tools.
"""


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _execute_tool(name: str, arguments: str) -> tuple[ProjectState, dict[str, Any]]:
    if name != "generate_structural_elements":
        raise ValueError(f"Unknown tool: {name}")

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e

    if "elements" not in args or not isinstance(args["elements"], list):
        raise ValueError("Missing or invalid 'elements' array")

    if len(args["elements"]) == 0:
        raise ValueError("elements array must not be empty")

    state = generate_structural_elements_from_dicts(args["elements"])
    summary = {
        "success": True,
        "element_count": len(state.elements),
        "shape_types": [e.shape_type for e in state.elements],
    }
    return state, summary


def run_chat_turn(
    messages: list[ChatMessage],
    project_state: ProjectState,
) -> tuple[str, list[str], ProjectState]:
    """Run one chat turn: OpenAI tool call -> geometry engine -> final reply."""
    statuses: list[str] = ["Parsing request..."]
    client = _client()
    statuses.append("Calling Steelera AI...")

    openai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_messages_to_openai(messages),
    ]

    if project_state.elements:
        openai_messages.append(
            {
                "role": "system",
                "content": (
                    f"Current model has {len(project_state.elements)} elements on screen. "
                    "Replace the full model when the user requests a new structure."
                ),
            }
        )

    current_state = project_state
    assistant_content = ""

    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            tools=STRUCTURAL_TOOLS,
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
            if name == "generate_structural_elements":
                statuses.append("Steelera AI is generating structure...")
                statuses.append("Computing member geometry...")

            try:
                new_state, summary = _execute_tool(name, tc.function.arguments or "{}")
                current_state = new_state
            except (ValueError, ValidationError) as e:
                summary = {"success": False, "error": str(e)}

            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(summary),
                }
            )

        statuses.append("Rendering structure...")
    else:
        assistant_content = assistant_content or (
            "I completed the structural update. Let me know if you want changes."
        )

    if not assistant_content:
        followup = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
        )
        assistant_content = followup.choices[0].message.content or (
            "Your structural model has been updated in the 3D viewport."
        )

    return assistant_content, statuses, current_state

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from catalog_loader import list_profiles
from core.env_loader import load_env
from core.geometry_engine import apply_macro_action, parse_add_structural_element
from core.shed_assembly import apply_modify_shed_assembly
from core.shed_params import (
    SHED_ASSEMBLY_ID,
    format_shed_assembly_context,
    shed_members_in,
)
from core.spatial_context import format_project_context
from schemas.chat import ChatMessage, ChatUiBlock, ShedChecklistPayload
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

Portal frame shed assembly (shed_1) — NEW shed workflow:
- When the user wants to CREATE, BUILD, or START a new portal-frame shed, you MUST call
  show_component_checklist (not modify_shed_assembly, not add_structural_element).
- Extract width_mm, length_mm, height, roof_style, roof_pitch_deg from their message (mm).
- After calling show_component_checklist, reply briefly that they can pick options in the checklist below.

Portal frame shed — MODIFY existing shed (CRITICAL):
- You are FORBIDDEN from answering text-only when the user requests a structural geometric change,
  layout change, or shed parameter change. You MUST call modify_shed_assembly in the same turn
  (it regenerates the full macro — equivalent to generate_shed_macro on the server).
- Read ACTIVE SHED ASSEMBLY for current x_spans / z_spans. When bays change, pass the FULL new
  comma-separated span string (not a delta). Example: z_spans were "5000, 5000, 5000" and user
  adds one 5000 mm bay along +Z → z_spans: "5000, 5000, 5000, 5000".
- Pass null for every field that does not change (strict tool schema).
- Examples: roof pitch 15° → roof_pitch_deg: 15; mono roof → roof_style: "mono_pitch";
  add X-bracing → use_bracing: true.
- Do NOT add individual shed members with add_structural_element when updating the shed macro.
- NEVER say the shed was updated, resized, or that a bay was added unless modify_shed_assembly
  returned success:true in the tool result.

Macro actions (duplicate / array / delete):
- When the user asks to copy, duplicate, array, multiply, or delete a member, call apply_macro_action — NOT multiple add_structural_element calls.
- ARRAY: target_element_id, count (copies to create, excluding original), spacing {{value, unit}}, axis = world offset direction (right/+X = X, up/+Y = Y, forward/+Z = Z).
- DELETE: target_element_id, action_type DELETE (set count/spacing/axis to null).
- If the user selected an element, use that id as target_element_id when they say "this" or "it".

Units: m, mm, ft, in, or auto (value<20 => meters, value>=20 => mm).

When adding to an existing model, APPEND new members — do not replace unless the user asks to rebuild.
Do not invent geometry in prose only—use the tool for every structural change.
NEVER claim members were added, duplicated, deleted, or that the shed changed unless a tool call
returned success:true.
For general questions without structure, respond without tools.
"""


def _selection_context(
    target_element_id: str | None,
    project_elements: list[ProjectElementMm] | None = None,
) -> str:
    if not target_element_id:
        return ""
    extra = (
        f"\n\n---\n"
        f"The user has currently selected element '{target_element_id}'. "
        f"If they ask to copy, array, multiply, or delete 'this' or 'it', "
        f"call apply_macro_action with this target_element_id."
    )
    if project_elements:
        selected = next(
            (element for element in project_elements if element.id == target_element_id),
            None,
        )
        if selected and selected.assembly_id == SHED_ASSEMBLY_ID:
            extra += (
                f" This member belongs to assembly '{SHED_ASSEMBLY_ID}'. "
                f"If they ask to resize or change the shed, call modify_shed_assembly."
            )
    return extra


def build_system_prompt(
    project_elements: list[ProjectElementMm],
    *,
    target_element_id: str | None = None,
) -> str:
    """Base prompt + readable inventory of already-built members."""
    context = format_project_context(project_elements)
    shed_ctx = format_shed_assembly_context(project_elements)
    selection = _selection_context(target_element_id, project_elements)
    return f"{BASE_SYSTEM_PROMPT}\n\n---\n{context}{shed_ctx}{selection}"


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


def _is_new_shed_request(text: str) -> bool:
    t = text.lower()
    build_words = (
        "build",
        "create",
        "design",
        "generate",
        "make",
        "start",
        "new",
        "need",
        "want",
        "give me",
        "draw",
    )
    shed_words = (
        "shed",
        "portal frame",
        "portal-frame",
        "warehouse",
        "building",
        "structure",
        "hangar",
        "barn",
    )
    return any(w in t for w in build_words) and any(w in t for w in shed_words)


def _is_layout_modify_request(text: str) -> bool:
    """Bay / span / extent changes without requiring the word 'shed'."""
    t = text.lower()
    layout_words = (
        "bay",
        "bays",
        "span",
        "spans",
        "frame",
        "frames",
        "spacing",
        "grid",
        "right",
        "left",
        "length",
        "width",
        "extend",
        "extension",
    )
    action_words = (
        "add",
        "remove",
        "delete",
        "another",
        "extra",
        "more",
        "extend",
        "shorten",
        "widen",
        "lengthen",
    )
    return any(w in t for w in layout_words) and any(w in t for w in action_words)


def _is_shed_param_request(text: str) -> bool:
    """Pitch, roof form, height, toggles — often without 'shed'."""
    t = text.lower()
    param_words = (
        "pitch",
        "roof",
        "eave",
        "height",
        "truss",
        "trusses",
        "bracing",
        "girt",
        "girts",
        "sag",
        "mono",
        "duo",
        "flat",
        "purlin",
    )
    change_words = (
        "raise",
        "lower",
        "change",
        "set",
        "make",
        "update",
        "increase",
        "decrease",
        "to ",
        "enable",
        "disable",
        "turn on",
        "turn off",
        "add",
        "remove",
        "degrees",
        "degree",
        "°",
    )
    return any(w in t for w in param_words) and any(w in t for w in change_words)


def _is_shed_modify_request(text: str) -> bool:
    t = text.lower()
    if _is_layout_modify_request(text) or _is_shed_param_request(text):
        return True
    shed_words = (
        "shed",
        "portal frame",
        "portal-frame",
        "warehouse",
        "building",
        "hangar",
    )
    change_words = (
        "higher",
        "taller",
        "wider",
        "longer",
        "shorter",
        "lower",
        "resize",
        "change",
        "update",
        "increase",
        "decrease",
        "make the",
        "add",
        "enable",
        "disable",
        "turn on",
        "turn off",
        "meter",
        "metre",
        "mm",
    )
    return any(w in t for w in shed_words) and any(w in t for w in change_words)


def _requires_structural_tool(
    text: str,
    *,
    has_shed: bool,
    has_elements: bool,
) -> bool:
    """User intent needs a tool call — not a prose-only reply."""
    if _is_new_shed_request(text) and not _is_shed_modify_request(text):
        return True
    if has_shed and _is_shed_modify_request(text):
        return True
    if has_elements and _is_macro_request(text):
        return True
    return False


def _forced_tool_for_turn(
    *,
    force_checklist: bool,
    force_shed: bool,
    force_macro: bool,
    tools_used: bool,
    structural_required: bool,
) -> str | None:
    if force_checklist and not tools_used:
        return "show_component_checklist"
    if force_shed and not tools_used:
        return "modify_shed_assembly"
    if force_macro and not tools_used:
        return "apply_macro_action"
    if structural_required and not tools_used:
        return "modify_shed_assembly"
    return None


def _execute_show_component_checklist(arguments: str) -> tuple[dict[str, Any], ChatUiBlock]:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e

    payload = ShedChecklistPayload.model_validate(args)
    ui_block = ChatUiBlock(type="show_component_checklist", payload=payload)
    return {"success": True, "checklist": True}, ui_block


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
) -> tuple[str, list[str], ProjectState, ChatUiBlock | None]:
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
    has_shed = bool(shed_members_in(elements, SHED_ASSEMBLY_ID))
    force_checklist = _is_new_shed_request(last_user_text) and not _is_shed_modify_request(
        last_user_text
    )
    force_shed = bool(
        has_shed
        and _is_shed_modify_request(last_user_text)
        and not force_checklist
    )
    structural_required = _requires_structural_tool(
        last_user_text,
        has_shed=has_shed,
        has_elements=bool(elements),
    )

    # Append mode when model already has members (supports "add beam on column")
    replace_next = len(elements) == 0
    assistant_content = ""
    tools_used = False
    shed_tool_used = False
    ui_block: ChatUiBlock | None = None

    for turn in range(MAX_TURNS):
        forced_name = _forced_tool_for_turn(
            force_checklist=force_checklist,
            force_shed=force_shed,
            force_macro=force_macro,
            tools_used=tools_used,
            structural_required=structural_required and has_shed,
        )
        tool_choice: Any = "auto"
        if forced_name:
            tool_choice = {
                "type": "function",
                "function": {"name": forced_name},
            }

        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            tools=ELEMENT_TOOLS,
            tool_choice=tool_choice,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            if (
                forced_name
                and not tools_used
                and turn < MAX_TURNS - 1
            ):
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                    }
                )
                openai_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You must call the required tool now with concrete arguments. "
                            f"Call {forced_name} immediately. Do not reply with text only."
                        ),
                    }
                )
                statuses.append(f"Retrying — requiring {forced_name}...")
                continue
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
            elif name == "modify_shed_assembly":
                statuses.append("Regenerating portal frame shed...")
                try:
                    elements, summary = apply_modify_shed_assembly(
                        elements,
                        tc.function.arguments or "{}",
                    )
                    ok = summary.get("success") is True
                    tools_used = tools_used or ok
                    shed_tool_used = shed_tool_used or ok
                    applied = summary.get("applied_params") or {}
                    statuses.append(
                        "Shed updated: "
                        f"{applied.get('width')}×{applied.get('length')} mm, "
                        f"height {applied.get('height')} mm, "
                        f"pitch {applied.get('roof_pitch_deg')}°..."
                    )
                except (ValueError, ValidationError) as e:
                    summary = {"success": False, "error": str(e)}
            elif name == "show_component_checklist":
                statuses.append("Preparing structural checklist...")
                try:
                    summary, block = _execute_show_component_checklist(
                        tc.function.arguments or "{}"
                    )
                    ui_block = block
                    tools_used = True
                    statuses.append("Checklist ready — confirm in chat.")
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

    if ui_block and not assistant_content:
        assistant_content = (
            "I've set up your portal frame shed from what you described. "
            "Review the structural options in the checklist below, then confirm to generate."
        )
    elif force_checklist and not tools_used:
        assistant_content = (
            "I couldn't open the shed checklist. "
            "Try rephrasing, e.g. “Build a 10 m × 40 m duo-pitch shed, 4 m eave height.”"
        )
    elif (force_shed or (structural_required and has_shed)) and not shed_tool_used:
        assistant_content = (
            "I couldn't apply that structural change to the shed. "
            "Please try again (e.g. specify bay width in mm or which dimension changes)."
        )
    elif force_macro and not tools_used:
        assistant_content = (
            "I couldn't apply that change to the selected member. "
            "Please try again with the member selected in the viewport."
        )
    elif not assistant_content:
        if tools_used:
            if shed_tool_used:
                assistant_content = (
                    "Done — the portal frame shed was regenerated with your updated parameters. "
                    "Check the 3D viewport."
                )
            else:
                assistant_content = (
                    "Structural update applied. Check the 3D viewport."
                )
        elif structural_required and not tools_used:
            assistant_content = (
                "I couldn't run a structural tool for that request. "
                "Generate a shed first, or rephrase the change."
            )
        else:
            followup = client.chat.completions.create(
                model=MODEL,
                messages=openai_messages,
            )
            assistant_content = followup.choices[0].message.content or (
                "How can I help with your structural model?"
            )

    if not ui_block:
        statuses.append("Rendering structure...")
    return assistant_content, statuses, ProjectState(
        version=3, projectElements=elements
    ), ui_block

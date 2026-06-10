import json
import os
import re
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from catalog_loader import list_families
from core.env_loader import load_env
from core.geometry_engine import apply_macro_action
from core.model_edit import update_member_profiles
from core.spatial_context import format_project_context
from core.grid_layout_utils import ensure_layout_members
from core.member_resolver import layout_to_macro_members
from core.operation_expander import expand_design
from core.clarification_parse import apply_inferred_clarification
from core.grid_intent import extract_grid_intent_from_text, merge_grid_intent_into_definition
from core.profile_overrides import apply_profile_overrides_to_layout
from core.structural_renderer import layout_to_api_dict
from core.structural_validator import validate_macro_members
from schemas.chat import ChatMessage, ChatUiBlock, SelectionContextPayload
from schemas.elements import ProjectElementMm
from schemas.project import ProjectState
from schemas.spatial_grid import StructuralGridLayout
from schemas.structural_ops import StructuralDesign
from tools.element_tool import CHAT_TOOLS

load_env()

MODEL = "gpt-4o-mini"
MAX_TURNS = 6

_CATALOG_SUMMARY = "; ".join(
    f"{f['family']} ({f['shape']}, {f['count']} sizes, h {int(f['min_h'])}-{int(f['max_h'])} mm)"
    for f in list_families()
)

BASE_SYSTEM_PROMPT = f"""You are a Structural Engineering Consultant for Steelera. You do the ENGINEERING
judgement; the Python engine does ALL geometry. You NEVER author individual members, never compute
coordinates, lengths, or angles, and never do trigonometry.

HOW TO BUILD A SHED (mandatory):
Call `submit_structural_grid_layout` with a `grid_definition` (parameters + capability toggles) and
`structural_members: []` (ALWAYS EMPTY). Python generates members from your toggles: columns,
rafters/trusses, tie beams, purlins, wall/gable girts, and X-bracing only when the corresponding
boolean flags are true. You only choose the parameters — do not list members yourself.

grid_definition fields:
- x_spans[]  = bay widths across the WIDTH (X), in mm. Sum = total width.
- z_spans[]  = portal-frame bay spacings along the LENGTH (Z), in mm. Sum = total length.
- height_mm  = eave height (mm).
- roof_pitch_deg = roof pitch in degrees (0 for flat).
- roof_style = "duo_pitch" | "mono_pitch" | "flat".
- mono_high_side = "A" or "B" (mono only): which side is the tall side. Default "B".
- use_truss (bool) + truss_type: trusses instead of solid rafters. Options:
  "pratt"|"howe"|"warren" (auto-panelled, any span/roof), "fink"|"king_post"|
  "queen_post"|"scissor" (symmetric duo-pitch gables), or "none". Pick the type
  the user names; default "pratt" when they just say "truss".
- x_bracing (bool): cross (X) bracing on the LONG side walls.
- gable_bracing (bool): cross (X) bracing on the two GABLE END walls.
- roof_bracing (bool): cross (X) bracing in the ROOF planes (end bays).
- sag_rods (bool): anti-sag rods between purlins.
- haunches (bool): tapered eave (knee) + apex haunches on RAFTER (portal) frames — standard
  detailing for portal sheds (ignored on truss frames).
- fly_braces (bool): small fly/flange braces restraining rafter inner flanges (purlin stays).
- base_plates (bool): steel base plates under every column / gable-post foot (clean IFC export).
- bottom_chord_restraint (bool): longitudinal runners restraining truss bottom chords (trusses only).
- generate_purlins (bool, default true), generate_wall_girts (bool, default true), generate_tie_beams (bool, default true).
- purlin_spacing_mm (default 1200), girt_spacing_mm (default 1500).
- column_profile (e.g. HEA200 / SHS300x300x10; null = default), bracing_profile (e.g. L50x50; null = default).
- purlin_profile / girt_profile (cold-formed Cee or Zed, e.g. C200x2.0 / Z200x2.0; null = default).
- sag_rod_profile (plain rod, e.g. ROD12 / ROD16; null = default), base_plate_profile (e.g. PL12 / PL20; null = default).
- truss_chord_profile (top + bottom chords, e.g. SHS120x120x6 / IPE200; null = default IPE200).
- truss_web_profile (web diagonals, e.g. L60x60x6 / L50x50; null = default L50x50).

Choosing spans:
- A single clear-span width → one x_span. e.g. 12 m wide → x_spans:[12000].
- "N bays" along the length → N z_spans. e.g. 25 m long in 5 bays → z_spans:[5000,5000,5000,5000,5000].
- If the user gives only total length + bay count, divide evenly.

Defaults when the user is silent: duo_pitch, 10° pitch, generate_purlins true, generate_wall_girts true,
generate_tie_beams true, truss off, bracing off, sag rods off, haunches/fly_braces/base_plates/
bottom_chord_restraint off. Honor explicit DISABLED / "do not generate" requests by setting the
matching boolean to false. Always set EVERY field in the schema (it is strict).

MODIFICATIONS: to resize or toggle a feature (add bracing, more bays, change pitch, etc.), call
`submit_structural_grid_layout` again with the FULL updated grid_definition and structural_members:[].
Each submission rebuilds the shed.

For a single-member duplicate/delete on an existing model, use apply_macro_action with the id.

EXAMPLE — "12 m wide, 25 m long, 5 bays, 4.5 m eave, 12° duo-pitch, with purlins and girts":
submit_structural_grid_layout({{
  "assembly_id": "shed_1", "replace_existing": true,
  "grid_definition": {{
    "x_spans": [12000], "z_spans": [5000,5000,5000,5000,5000],
    "height_mm": 4500, "roof_pitch_deg": 12, "roof_style": "duo_pitch",
    "mono_high_side": "B", "use_truss": false, "truss_type": "none",
    "x_bracing": false, "gable_bracing": false, "roof_bracing": false, "sag_rods": false,
    "haunches": false, "fly_braces": false, "base_plates": false, "bottom_chord_restraint": false,
    "generate_purlins": true, "generate_wall_girts": true, "generate_tie_beams": true,
    "purlin_spacing_mm": 1200, "girt_spacing_mm": 1500,
    "column_profile": null, "bracing_profile": null,
    "purlin_profile": null, "girt_profile": null,
    "sag_rod_profile": null, "base_plate_profile": null,
    "truss_chord_profile": null, "truss_web_profile": null
  }},
  "structural_members": []
}})

After the tool succeeds, briefly summarise what was built (dimensions, roof, bays, and which systems
are included). Never claim a model was built without a successful submit_structural_grid_layout call.

Profile catalog (European, EN): {_CATALOG_SUMMARY}. Units: mm. Use full designations
(e.g. IPE300, HEA200, UB457x191x67, RHS120x80x5, CHS168.3x5, L100x100x10) when specifying sections.

WORKSPACE CONSULTATION (when a model already exists in the viewport):
- Before changing the model, confirm intent when scope or action is unclear.
- Ask at most ONE clarifying question per turn (max TWO clarification turns total).
- When offering choices, you MUST call `ask_clarification` with 2–4 short tap options.
  NEVER write numbered lists (1. 2. 3.) in plain text — the UI renders options as buttons.
- On an EXISTING model, profile/section changes MUST use `update_member_profile` — NEVER
  `submit_structural_grid_layout`. Full grid rebuild is only for new sheds or explicit
  resize/bay-count/roof-type layout changes with dimensions.
- Before `update_member_profile`, confirm scope if unclear: this member only, all members
  of that type (e.g. all columns), this frame only, or user picks members in the viewport.
  Use `ask_clarification` with scope options — do not assume "all columns".
- Accept any catalog profile the user types (e.g. HEA380) even if not in your suggestion list.
- Do NOT call submit_structural_grid_layout or apply_macro_action until intent is clear,
  unless the user gave a complete explicit command (exact dimensions, or "yes/proceed/do it").
- For custom bracing at user-chosen points, use `request_viewport_node_pick` (single_brace or full_x)
  instead of rebuilding the whole shed.
- To insert a portal frame at a bay line the user picks, use `request_viewport_grid_pick`.
- Prefer surgical description for profile tweaks; the UI may apply /api/model edits directly.
- Explain and advise freely; only mutate geometry when the user has confirmed what they want.
"""


_CONFIRM_PHRASES = (
    "yes", "yep", "yeah", "ok", "okay", "do it", "proceed", "go ahead",
    "confirm", "sounds good", "that's fine", "correct", "exactly",
)


def _selection_context(
    target_element_id: str | None,
    selection: SelectionContextPayload | None = None,
) -> str:
    if selection is not None:
        lines = [
            "\n\n---\nViewport selection (user clicked this member):",
            f"- id: {selection.element_id}",
            f"- type: {selection.element_type or 'unknown'}",
            f"- label: {selection.label or 'member'}",
        ]
        if selection.location_subtitle:
            lines.append(f"- location: {selection.location_subtitle}")
        if selection.profile:
            lines.append(f"- profile: {selection.profile}")
        if selection.frame_index is not None:
            lines.append(f"- frame_index (0-based): {selection.frame_index}")
        lines.append(
            "- Scope edits to this member unless the user asks for all columns/purlins/frame/etc."
        )
        return "\n".join(lines)

    if not target_element_id:
        return ""
    return (
        f"\n\n---\nSelected element: '{target_element_id}'. "
        f"Scope edits to this member unless the user asks for a wider scope."
    )


def build_system_prompt(
    project_elements: list[ProjectElementMm],
    *,
    target_element_id: str | None = None,
    selection_context: SelectionContextPayload | None = None,
) -> str:
    context = format_project_context(
        project_elements,
        focus_element_id=target_element_id,
        selection=selection_context,
    )
    selection = _selection_context(target_element_id, selection_context)
    return f"{BASE_SYSTEM_PROMPT}\n\n---\n{context}{selection}"


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _is_macro_request(text: str) -> bool:
    t = text.lower()
    return any(
        word in t
        for word in ("duplicate", "copy", "array", "multiply", "clone", "delete")
    )


def _user_confirmed(text: str) -> bool:
    t = text.lower().strip()
    return any(p in t for p in _CONFIRM_PHRASES)


def _has_clear_dimensions(text: str) -> bool:
    t = text.lower()
    return bool(
        re.search(r"\d+\s*[x×]\s*\d+", t)
        or (
            re.search(r"\d+\s*(?:m|mm)\b", t)
            and any(w in t for w in ("wide", "long", "length", "width", "bay", "eave", "high"))
        )
    )


_PROFILE_IN_TEXT_RE = re.compile(
    r"\b(hea\d+|heb\d+|ipe\d+|rhs|shs|switch to|profile|section size)\b",
    re.IGNORECASE,
)


def _is_surgical_edit_request(text: str) -> bool:
    """Profile / member edits — must not trigger full shed rebuild."""
    t = text.lower().strip()
    if _PROFILE_IN_TEXT_RE.search(t):
        return True
    if re.search(r"\b(switch to|upsize|larger section|change section|make it)\b", t):
        return True
    if _is_macro_request(t):
        return True
    return False


def _is_explicit_layout_request(text: str) -> bool:
    """Only force full layout rebuild when intent is unambiguous."""
    t = text.lower().strip()
    if _is_macro_request(t):
        return False
    if _is_surgical_edit_request(t):
        return False
    if _user_confirmed(t) and len(t.split()) <= 4:
        return False
    if _user_confirmed(t) and _has_clear_dimensions(t):
        return True
    if _has_clear_dimensions(t) and any(
        w in t for w in ("build", "create", "design", "generate", "make", "new shed")
    ):
        return True
    return False


def _is_explicit_macro_request(text: str) -> bool:
    t = text.lower()
    if not _is_macro_request(t):
        return False
    if _user_confirmed(t):
        return True
    # "delete this column" with selection is explicit enough
    return bool(re.search(r"\b(delete|duplicate|copy|clone)\b", t))


def _clarification_ui_block(args: dict[str, Any]) -> ChatUiBlock:
    options = args.get("options") or []
    payload: dict[str, Any] = {
        "question": str(args.get("question", "")),
        "options": [
            {"label": str(o.get("label", "")), "value": str(o.get("value", ""))}
            for o in options
            if isinstance(o, dict)
        ],
    }
    if args.get("allowCustom"):
        payload["allowCustom"] = True
        if args.get("customPlaceholder"):
            payload["customPlaceholder"] = str(args["customPlaceholder"])
    return ChatUiBlock(type="workspace_quick_replies", payload=payload)


def _node_pick_ui_block(args: dict[str, Any]) -> ChatUiBlock:
    intent = str(args.get("intent", "single_brace"))
    if intent not in ("single_brace", "full_x"):
        intent = "single_brace"
    profile = args.get("profile")
    return ChatUiBlock(
        type="viewport_node_pick",
        payload={
            "intent": intent,
            "needed": 4 if intent == "full_x" else 2,
            "profile": str(profile) if profile else None,
            "instruction": str(args.get("instruction", "Click connection points on the model.")),
        },
    )


def _grid_pick_ui_block(args: dict[str, Any]) -> ChatUiBlock:
    return ChatUiBlock(
        type="viewport_grid_pick",
        payload={
            "instruction": str(
                args.get("instruction", "Click a numbered frame line on the model.")
            ),
        },
    )


def _parse_grid_layout(arguments: str, *, user_text: str = "") -> StructuralGridLayout:
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e
    layout = StructuralGridLayout.model_validate(raw)
    # Python OWNS the geometry: ignore any AI-authored members and always rebuild
    # the complete, correct shed from the parametric grid_definition + toggles.
    # AI tool arguments are authoritative; regex intent only fills non-boolean hints.
    intent = extract_grid_intent_from_text(user_text)
    gd = merge_grid_intent_into_definition(
        layout.grid_definition,
        intent,
        fill_gaps_only=True,
    )
    layout = layout.model_copy(
        update={"grid_definition": gd, "structural_members": []},
    )
    layout = ensure_layout_members(layout)
    return apply_profile_overrides_to_layout(layout, user_text=user_text)


def _design_to_validated_layout(
    arguments: str,
) -> tuple[StructuralGridLayout, list[str]]:
    """Expand operations → layout, resolve to mm, and run structural validation."""
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e
    design = StructuralDesign.model_validate(raw)
    layout = expand_design(design)
    macro_members = layout_to_macro_members(layout)
    errors = validate_macro_members(macro_members)
    return layout, errors


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


_PROFILE_NAME_RE = re.compile(
    r"^(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+|L\d+[\dxX/-]*)$",
    re.IGNORECASE,
)
_PROFILE_SWITCH_RE = re.compile(
    r"(?:yes,?\s*)?switch to\s+"
    r"(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)\b",
    re.IGNORECASE,
)
_SCOPE_APPLY_RE = re.compile(
    r"apply\s+(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)\s+to\s+(.+)",
    re.IGNORECASE,
)


def _pending_profile_from_messages(messages: list[ChatMessage]) -> str | None:
    for msg in reversed(messages):
        if msg.role != "assistant":
            continue
        apply_m = re.search(
            r"Apply\s+(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+)\s+to which",
            msg.content,
            re.IGNORECASE,
        )
        if apply_m:
            return apply_m.group(1).upper()
    for msg in reversed(messages):
        switch_m = _PROFILE_SWITCH_RE.search(msg.content)
        if switch_m:
            return switch_m.group(1).upper()
        name_m = _PROFILE_NAME_RE.match(msg.content.strip())
        if name_m:
            return name_m.group(1).upper()
    return None


def _reference_element_id(
    target_element_id: str | None,
    selection: SelectionContextPayload | None,
) -> str | None:
    ref = (target_element_id or "").strip()
    if ref:
        return ref
    if selection and selection.element_id:
        return selection.element_id.strip()
    return None


def _scope_from_phrase(phrase: str) -> str:
    p = phrase.lower().strip()
    if "this frame" in p or "frame only" in p:
        return "frame"
    if p.startswith("all ") or "all columns" in p or "all purlins" in p:
        return "element_type"
    return "selection"


def _scope_clarification_block(profile: str, element_type: str) -> ChatUiBlock:
    et_label = element_type.replace("_", " ") if element_type else "members"
    return ChatUiBlock(
        type="workspace_quick_replies",
        payload={
            "question": f"Apply {profile} to which members?",
            "options": [
                {
                    "label": "This member only",
                    "value": f"Apply {profile} to this member only",
                },
                {
                    "label": f"All {et_label}s",
                    "value": f"Apply {profile} to all {et_label}s",
                },
                {
                    "label": "This frame only",
                    "value": f"Apply {profile} to this frame only",
                },
                {
                    "label": "Pick on model",
                    "value": "__pick_on_model__",
                },
            ],
            "allowCustom": True,
            "customPlaceholder": "Type any section e.g. HEA380",
        },
    )


def _try_profile_edit_shortcut(
    messages: list[ChatMessage],
    elements: list[ProjectElementMm],
    *,
    target_element_id: str | None,
    selection: SelectionContextPayload | None,
) -> tuple[str, list[ProjectElementMm], ChatUiBlock | None] | None:
    if not messages or messages[-1].role != "user":
        return None
    if not elements:
        return None

    ref_id = _reference_element_id(target_element_id, selection)
    last = messages[-1].content.strip()

    if last == "__pick_on_model__":
        profile = _pending_profile_from_messages(messages)
        if profile:
            return (
                f"Click each member in the viewport, then use **Section size** "
                f"in the bar below to set {profile}.",
                elements,
                None,
            )
        return (
            "Click each member in the viewport, then use **Section size** "
            "in the bar below to change its section.",
            elements,
            None,
        )

    scope_m = _SCOPE_APPLY_RE.search(last)
    if scope_m:
        if not ref_id:
            return (
                "Select a member in the viewport first, then choose the scope again.",
                elements,
                None,
            )
        profile = scope_m.group(1).upper()
        scope = _scope_from_phrase(scope_m.group(2))
        try:
            updated, changed = update_member_profiles(
                elements,
                profile=profile,
                reference_element_id=ref_id,
                scope=scope,
            )
        except ValueError as e:
            return str(e), elements, None
        scope_label = scope.replace("_", " ")
        return (
            f"Updated {len(changed)} member(s) to {profile} ({scope_label}).",
            updated,
            None,
        )

    profile: str | None = None
    switch_m = _PROFILE_SWITCH_RE.search(last)
    if switch_m:
        profile = switch_m.group(1).upper()
    else:
        name_m = _PROFILE_NAME_RE.match(last)
        if name_m:
            profile = name_m.group(1).upper()

    if not profile:
        return None

    if not ref_id:
        return (
            "Select a member in the viewport first, then choose or type the section size.",
            elements,
            None,
        )

    et = (selection.element_type if selection else "") or "member"
    ui = _scope_clarification_block(profile, et)
    return (
        f"Apply {profile} to which members?",
        elements,
        ui,
    )


def run_chat_turn(
    messages: list[ChatMessage],
    project_state: ProjectState,
    *,
    spatial_context: str | None = None,
    target_element_id: str | None = None,
    selection_context: SelectionContextPayload | None = None,
) -> tuple[str, list[str], ProjectState, ChatUiBlock | None, dict[str, Any] | None]:
    """
    AI submits grid layout + structural_members; frontend calls /api/macro/generate-shed.
    """
    statuses: list[str] = ["Parsing request..."]
    client = _client()
    statuses.append("Calling Steelera AI (gpt-4o-mini)...")

    elements: list[ProjectElementMm] = list(project_state.projectElements)
    shortcut = _try_profile_edit_shortcut(
        messages,
        elements,
        target_element_id=target_element_id,
        selection=selection_context,
    )
    if shortcut is not None:
        assistant_content, elements, ui_block = shortcut
        statuses.append("Done.")
        return (
            assistant_content,
            statuses,
            ProjectState(version=3, projectElements=elements),
            ui_block,
            None,
        )

    system_content = spatial_context or build_system_prompt(
        elements,
        target_element_id=target_element_id,
        selection_context=selection_context,
    )

    openai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        *_messages_to_openai(messages),
    ]

    last_user_text = messages[-1].content if messages else ""
    has_model = bool(elements)
    force_macro = has_model and _is_explicit_macro_request(last_user_text)
    force_layout = _is_explicit_layout_request(last_user_text)

    assistant_content = ""
    tools_used = False
    config_submitted: dict[str, Any] | None = None
    ui_block: ChatUiBlock | None = None
    profile_done = False

    for turn in range(MAX_TURNS):
        forced_name: str | None = None
        if force_layout and config_submitted is None:
            forced_name = "submit_structural_grid_layout"
        elif force_macro and not tools_used:
            forced_name = "apply_macro_action"

        tool_choice: Any = "auto"
        if forced_name:
            tool_choice = {
                "type": "function",
                "function": {"name": forced_name},
            }

        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            tools=CHAT_TOOLS,
            tool_choice=tool_choice,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            if forced_name and not tools_used and turn < MAX_TURNS - 1:
                openai_messages.append(
                    {"role": "assistant", "content": msg.content or ""}
                )
                openai_messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Call `{forced_name}` now with complete parameters. "
                            "No prose-only replies."
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
            if name == "submit_structural_design":
                statuses.append("Expanding & validating structural design...")
                try:
                    layout, errors = _design_to_validated_layout(
                        tc.function.arguments or "{}"
                    )
                    if errors:
                        statuses.append(
                            f"Validation found {len(errors)} issue(s); asking AI to fix..."
                        )
                        summary = {
                            "success": False,
                            "validation_errors": errors,
                            "hint": (
                                "Your design is structurally invalid. Fix every issue "
                                "above and call submit_structural_design again. Common fix: "
                                "make high-side/interior column tops use elevation 'roof' "
                                "so they meet the rafters."
                            ),
                        }
                    else:
                        config_submitted = layout_to_api_dict(layout)
                        tools_used = True
                        gd = layout.grid_definition
                        statuses.append(
                            f"Design valid: {len(layout.structural_members)} members "
                            f"across {len(gd.z_spans)} Z-bays."
                        )
                        summary = {
                            "success": True,
                            "structural_grid_layout": config_submitted,
                        }
                except (ValueError, ValidationError) as e:
                    summary = {"success": False, "error": str(e)}
            elif name == "submit_structural_grid_layout":
                if has_model and _is_surgical_edit_request(last_user_text):
                    summary = {
                        "success": False,
                        "error": (
                            "Existing model: use update_member_profile for section changes. "
                            "Do not rebuild the shed."
                        ),
                    }
                else:
                    statuses.append("Validating spatial grid layout...")
                    try:
                        layout = _parse_grid_layout(
                            tc.function.arguments or "{}",
                            user_text=last_user_text,
                        )
                        config_submitted = layout_to_api_dict(layout)
                        tools_used = True
                        gd = layout.grid_definition
                        statuses.append(
                            f"Grid ready: {len(gd.z_spans)} Z-bays, "
                            f"{len(gd.x_spans)} X-bays, "
                            f"{len(layout.structural_members)} members..."
                        )
                        summary = {
                            "success": True,
                            "structural_grid_layout": config_submitted,
                        }
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
                except (ValueError, ValidationError) as e:
                    summary = {"success": False, "error": str(e)}
            elif name == "update_member_profile":
                statuses.append("Updating member profile…")
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    profile = str(args.get("profile", "")).strip()
                    scope = str(args.get("scope", "selection"))
                    ref = str(args.get("reference_element_id") or "").strip()
                    if not ref:
                        ref = _reference_element_id(target_element_id, selection_context) or ""
                    if not ref:
                        raise ValueError(
                            "Select a member in the viewport or provide reference_element_id."
                        )
                    if not profile:
                        raise ValueError("profile is required")
                    elements, changed = update_member_profiles(
                        elements,
                        profile=profile,
                        reference_element_id=ref,
                        scope=scope,
                    )
                    tools_used = True
                    assistant_content = (
                        f"Updated {len(changed)} member(s) to {profile} "
                        f"({scope.replace('_', ' ')})."
                    )
                    summary = {
                        "success": True,
                        "changed_ids": changed,
                        "profile": profile,
                        "scope": scope,
                    }
                    profile_done = True
                except ValueError as e:
                    summary = {"success": False, "error": str(e)}
            elif name == "ask_clarification":
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                ui_block = _clarification_ui_block(args)
                assistant_content = str(
                    args.get("question") or "Which option do you prefer?"
                )
                tools_used = True
                summary = {"success": True, "ui_only": True}
            elif name == "request_viewport_node_pick":
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                ui_block = _node_pick_ui_block(args)
                assistant_content = str(
                    args.get("instruction") or "Click connection points on the model."
                )
                tools_used = True
                summary = {"success": True, "ui_only": True}
            elif name == "request_viewport_grid_pick":
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                ui_block = _grid_pick_ui_block(args)
                assistant_content = str(
                    args.get("instruction") or "Click a frame line on the model."
                )
                tools_used = True
                summary = {"success": True, "ui_only": True}
            else:
                summary = {
                    "success": False,
                    "error": f"Unknown tool: {name}. Use submit_structural_grid_layout.",
                }

            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(summary),
                }
            )

            if summary.get("success") and name == "update_member_profile":
                profile_done = True
                break

            if ui_block is not None and summary.get("ui_only"):
                break

        # A structure was submitted successfully — stop here so a later "auto" turn
        # cannot overwrite the Python-built layout with a different tool call.
        if config_submitted is not None:
            break

        if ui_block is not None:
            break

        if profile_done:
            break

    if force_layout and not config_submitted and ui_block is None:
        assistant_content = (
            "I could not submit a valid shed layout. "
            "Tell me the width, length (or bay count), eave height, and roof type and I will rebuild it."
        )
    elif not assistant_content:
        if ui_block is not None:
            pass
        elif config_submitted:
            try:
                openai_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The shed was generated successfully by the engine. In 3-6 short "
                            "lines, summarise what was built (dimensions, roof type/pitch, bay "
                            "count, and which systems are included). Do not call any tools."
                        ),
                    }
                )
                followup = client.chat.completions.create(
                    model=MODEL,
                    messages=openai_messages,
                )
                assistant_content = (
                    followup.choices[0].message.content
                    or "Shed generated. Check the 3D viewport."
                )
            except Exception:
                assistant_content = "Shed generated. Check the 3D viewport."
        elif tools_used:
            assistant_content = "Update applied. Check the 3D viewport."
        else:
            followup = client.chat.completions.create(
                model=MODEL,
                messages=openai_messages,
            )
            assistant_content = followup.choices[0].message.content or (
                "How can I help with your structural layout?"
            )

    statuses.append("Done.")
    assistant_content, ui_block = apply_inferred_clarification(
        assistant_content,
        ui_block,
    )
    return (
        assistant_content,
        statuses,
        ProjectState(version=3, projectElements=elements),
        ui_block,
        config_submitted,
    )

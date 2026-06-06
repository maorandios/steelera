import json
import os
import re
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from catalog_loader import list_families
from core.env_loader import load_env
from core.geometry_engine import apply_macro_action
from core.spatial_context import format_project_context
from core.grid_layout_utils import ensure_layout_members
from core.member_resolver import layout_to_macro_members
from core.operation_expander import expand_design
from core.profile_overrides import apply_profile_overrides_to_layout
from core.structural_renderer import layout_to_api_dict
from core.structural_validator import validate_macro_members
from schemas.chat import ChatMessage, ChatUiBlock
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
`structural_members: []` (ALWAYS EMPTY). Python then generates the COMPLETE, geometrically perfect
shed for you: columns, rafters or trusses, eave/ridge tie beams, roof purlins (seated on rafters),
wall girts on both side walls, gable posts + gable girts on the end walls, plus bracing and sag rods
when toggled on. You only choose the parameters — do not list members yourself.

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
- generate_wall_girts (bool, default true), generate_tie_beams (bool, default true).
- purlin_spacing_mm (default 1200), girt_spacing_mm (default 1500).
- column_profile (e.g. HEA200 / SHS300x300x10; null = default), bracing_profile (e.g. L50x50; null = default).
- purlin_profile / girt_profile (cold-formed Cee or Zed, e.g. C200x2.0 / Z200x2.0; null = default).
- sag_rod_profile (plain rod, e.g. ROD12 / ROD16; null = default), base_plate_profile (e.g. PL12 / PL20; null = default).

Choosing spans:
- A single clear-span width → one x_span. e.g. 12 m wide → x_spans:[12000].
- "N bays" along the length → N z_spans. e.g. 25 m long in 5 bays → z_spans:[5000,5000,5000,5000,5000].
- If the user gives only total length + bay count, divide evenly.

Defaults when the user is silent: duo_pitch, 10° pitch, generate_wall_girts true, generate_tie_beams
true, truss off, bracing off, sag rods off, haunches/fly_braces/base_plates/bottom_chord_restraint
off. Always set EVERY field in the schema (it is strict).

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
    "generate_wall_girts": true, "generate_tie_beams": true,
    "purlin_spacing_mm": 1200, "girt_spacing_mm": 1500,
    "column_profile": null, "bracing_profile": null,
    "purlin_profile": null, "girt_profile": null,
    "sag_rod_profile": null, "base_plate_profile": null
  }},
  "structural_members": []
}})

After the tool succeeds, briefly summarise what was built (dimensions, roof, bays, and which systems
are included). Never claim a model was built without a successful submit_structural_grid_layout call.

Profile catalog (European, EN): {_CATALOG_SUMMARY}. Units: mm. Use full designations
(e.g. IPE300, HEA200, UB457x191x67, RHS120x80x5, CHS168.3x5, L100x100x10) when specifying sections.
"""


def _selection_context(target_element_id: str | None) -> str:
    if not target_element_id:
        return ""
    return (
        f"\n\n---\nSelected element: '{target_element_id}'. "
        f"For copy/array/delete, call apply_macro_action with this id."
    )


def build_system_prompt(
    project_elements: list[ProjectElementMm],
    *,
    target_element_id: str | None = None,
) -> str:
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


def _is_macro_request(text: str) -> bool:
    t = text.lower()
    return any(
        word in t
        for word in ("duplicate", "copy", "array", "multiply", "clone", "delete")
    )


def _is_structural_layout_request(text: str) -> bool:
    t = text.lower()
    if _is_macro_request(text):
        return False
    keywords = (
        "build", "create", "design", "generate", "make", "shed", "portal",
        "frame", "warehouse", "structure", "bracing", "purlin", "girt",
        "truss", "rafter", "column", "bay", "roof", "add", "enable",
        "resize", "change", "update", "remove", "disable", "wider", "longer",
        "מחסן", "מסגרת", "גג", "פורטל", "קורה", "עמוד",
    )
    if any(w in t for w in keywords):
        return True
    # e.g. 10x30m, 10×30 m, 4000mm
    return bool(
        re.search(r"\d+\s*[x×]\s*\d+", t)
        or re.search(r"\d+\s*(?:m|mm)\b", t)
    )


def _parse_grid_layout(arguments: str, *, user_text: str = "") -> StructuralGridLayout:
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid tool arguments JSON: {e}") from e
    layout = StructuralGridLayout.model_validate(raw)
    # Python OWNS the geometry: ignore any AI-authored members and always rebuild
    # the complete, correct shed from the parametric grid_definition + toggles.
    layout = layout.model_copy(update={"structural_members": []})
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


def run_chat_turn(
    messages: list[ChatMessage],
    project_state: ProjectState,
    *,
    spatial_context: str | None = None,
    target_element_id: str | None = None,
) -> tuple[str, list[str], ProjectState, ChatUiBlock | None, dict[str, Any] | None]:
    """
    AI submits grid layout + structural_members; frontend calls /api/macro/generate-shed.
    """
    statuses: list[str] = ["Parsing request..."]
    client = _client()
    statuses.append("Calling Steelera AI (gpt-4o-mini)...")

    elements: list[ProjectElementMm] = list(project_state.projectElements)
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
    force_layout = _is_structural_layout_request(last_user_text)

    assistant_content = ""
    tools_used = False
    config_submitted: dict[str, Any] | None = None
    ui_block: ChatUiBlock | None = None

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
                        f"{len(gd.x_spans)} X-bays, {len(layout.structural_members)} members..."
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

        # A structure was submitted successfully — stop here so a later "auto" turn
        # cannot overwrite the Python-built layout with a different tool call.
        if config_submitted is not None:
            break

    if force_layout and not config_submitted:
        assistant_content = (
            "I could not submit a valid shed layout. "
            "Tell me the width, length (or bay count), eave height, and roof type and I will rebuild it."
        )
    elif not assistant_content:
        if config_submitted:
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
    return (
        assistant_content,
        statuses,
        ProjectState(version=3, projectElements=elements),
        ui_block,
        config_submitted,
    )

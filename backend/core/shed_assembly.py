"""Regenerate shed assemblies in a project element list."""

from __future__ import annotations

import json
from typing import Any

from core.geometry_engine import (
    generate_shed_macro,
    macro_members_to_project_elements,
)
from core.project_session import get_shed_params, set_shed_params
from core.shed_params import (
    SHED_ASSEMBLY_ID,
    infer_shed_params_from_elements,
    merge_shed_param_overrides,
    shed_members_in,
)
from schemas.elements import ProjectElementMm


def apply_modify_shed_assembly(
    elements: list[ProjectElementMm],
    arguments: str,
    assembly_id: str = SHED_ASSEMBLY_ID,
) -> tuple[list[ProjectElementMm], dict[str, Any]]:
    """
    Replace all members in assembly_id with a freshly generated shed.
    Merges optional overrides onto stored or inferred parameters.
    """
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc

    shed_members = shed_members_in(elements, assembly_id)
    if not shed_members:
        raise ValueError(
            f"No assembly '{assembly_id}' in the model. "
            "Generate a portal frame shed first."
        )

    stored = get_shed_params(assembly_id)
    current = stored or infer_shed_params_from_elements(shed_members)
    params = merge_shed_param_overrides(current, raw)

    if params.get("width", 0) <= 0 or params.get("length", 0) <= 0 or params["height"] <= 0:
        raise ValueError("width, length, and height must be positive")
    if params["roof_pitch_deg"] < 0 or params["roof_pitch_deg"] >= 90:
        raise ValueError("roof_pitch_deg must be between 0 and 90")

    roof_style = str(params.get("roof_style", "duo_pitch"))
    pitch_deg = 0.0 if roof_style == "flat" else float(params["roof_pitch_deg"])
    macro_members = generate_shed_macro(
        assembly_id=assembly_id,
        x_spans=params["x_spans"],
        z_spans=params["z_spans"],
        height=float(params["height"]),
        roof_pitch_deg=pitch_deg,
        roof_style=roof_style,
        purlin_spacing=float(params["purlin_spacing"]),
        girt_spacing_mm=float(params.get("girt_spacing_mm", 1500.0)),
        use_truss=bool(params.get("use_truss", False)),
        use_bracing=bool(params.get("use_bracing", False)),
        use_sag_rods=bool(params.get("use_sag_rods", False)),
        generate_wall_girts=bool(params.get("generate_wall_girts", True)),
        generate_tie_beams=bool(params.get("generate_tie_beams", True)),
    )
    new_shed = macro_members_to_project_elements(macro_members)
    other = [element for element in elements if element.assembly_id != assembly_id]
    result = other + new_shed

    set_shed_params(assembly_id, params)

    return result, {
        "success": True,
        "assembly_id": assembly_id,
        "applied_params": params,
        "total_elements": len(result),
        "shed_member_count": len(new_shed),
    }

"""
Universal structural renderer — grid definition + structural_members → project elements.
"""

from __future__ import annotations

import json
from typing import Any

from core.geometry_engine import macro_members_to_project_elements
from core.grid_member_catalog import members_from_shed_config
from core.ifc_topology import build_topology_from_layout, stamp_elements_with_topology
from core.member_resolver import layout_to_macro_members
from core.spatial_grid import StructuralGridEngine
from schemas.elements import ProjectElementMm
from schemas.shed_assembly_config import ShedAssemblyConfig
from schemas.spatial_grid import GridDefinition, StructuralGridLayout


def apply_structural_grid_layout(
    arguments: str,
    existing: list[ProjectElementMm],
    *,
    replace_session: bool,
) -> tuple[list[ProjectElementMm], dict[str, Any], StructuralGridLayout]:
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc

    layout = StructuralGridLayout.model_validate(raw)
    macro_members = layout_to_macro_members(layout)
    topology = build_topology_from_layout(layout)
    rendered = stamp_elements_with_topology(
        macro_members_to_project_elements(macro_members),
        topology,
    )

    if layout.replace_existing or replace_session:
        kept = [
            element
            for element in existing
            if element.assembly_id != layout.assembly_id
        ]
        result = kept + rendered
    else:
        result = list(existing) + rendered

    grid = StructuralGridEngine.from_definition(layout.grid_definition)
    return result, {
        "success": True,
        "assembly_id": layout.assembly_id,
        "member_count": len(rendered),
        "total_elements": len(result),
        "grid_summary": grid.grid_summary(),
        "structural_topology": topology.model_dump(),
    }, layout


def apply_shed_assembly_config(
    arguments: str,
    existing: list[ProjectElementMm],
    *,
    replace_session: bool,
) -> tuple[list[ProjectElementMm], dict[str, Any], StructuralGridLayout]:
    """Legacy parametric config → auto grid catalog → same resolver path."""
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc

    config = ShedAssemblyConfig.model_validate(raw).with_default_bays()
    gp = config.global_parameters
    layout = StructuralGridLayout(
        assembly_id=config.assembly_id,
        replace_existing=config.replace_existing,
        grid_definition=GridDefinition(
            x_spans=list(config.grid_layout.x_spans),
            z_spans=list(config.grid_layout.z_spans),
            height_mm=gp.height_mm,
            roof_pitch_deg=0.0 if gp.roof_style == "flat" else gp.roof_pitch_deg,
            roof_style=gp.roof_style,
        ),
        structural_members=members_from_shed_config(config),
    )
    return apply_structural_grid_layout(
        layout.model_dump_json(),
        existing,
        replace_session=replace_session,
    )


def layout_to_api_dict(layout: StructuralGridLayout) -> dict[str, Any]:
    """Serialize for /api/macro/generate-shed and frontend."""
    return layout.model_dump()

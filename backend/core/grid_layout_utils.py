"""Helpers to complete structural grid layouts before resolution."""

from __future__ import annotations

from core.grid_member_catalog import members_from_grid_definition
from core.grid_normalize import normalize_layout
from schemas.spatial_grid import StructuralGridLayout


def ensure_layout_members(layout: StructuralGridLayout) -> StructuralGridLayout:
    layout = normalize_layout(layout)
    if layout.structural_members:
        return layout
    generated = members_from_grid_definition(
        layout.grid_definition,
        assembly_id=layout.assembly_id,
    )
    return layout.model_copy(update={"structural_members": generated})

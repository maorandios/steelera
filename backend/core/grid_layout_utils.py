"""Helpers to complete structural grid layouts before resolution."""

from __future__ import annotations

from core.grid_member_catalog import members_from_grid_definition
from core.grid_normalize import normalize_layout
from schemas.spatial_grid import StructuralGridLayout


def ensure_layout_members(layout: StructuralGridLayout) -> StructuralGridLayout:
    layout = normalize_layout(layout)
    gd = layout.grid_definition
    # Trussed / mono-pitch sheds must always come from the catalog — stale AI/hand
    # members (especially roof/side X-bracing or old multi-panel mono trusses) must
    # not bypass Python-owned geometry.
    if (
        getattr(gd, "use_truss", False)
        or not layout.structural_members
        or gd.roof_style == "mono_pitch"
    ):
        generated = members_from_grid_definition(
            gd,
            assembly_id=layout.assembly_id,
        )
        return layout.model_copy(update={"structural_members": generated})
    return layout

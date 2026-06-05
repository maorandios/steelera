"""
Shed geometry — universal spatial grid architecture.

No element-specific generation loops. Grid matrix + member resolver only.
"""

from __future__ import annotations

from typing import Any

from core.grid_member_catalog import members_from_shed_config
from core.member_resolver import layout_to_macro_members, resolve_structural_members
from core.roof_geometry import (
    RoofGeometry,
    compute_roof_geometry,
    normalize_roof_style_and_pitch,
    roof_elevation_at_x,
)
from core.spatial_grid import StructuralGridEngine
from schemas.shed_assembly_config import ShedAssemblyConfig
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

# Re-exports for tests and legacy imports
__all__ = [
    "RoofGeometry",
    "StructuralGridEngine",
    "compute_roof_geometry",
    "generate_shed_from_assembly_config",
    "generate_shed_from_grid_layout",
    "generate_shed_macro",
    "layout_to_macro_members",
    "normalize_roof_style_and_pitch",
    "roof_elevation_at_x",
]


def generate_shed_from_grid_layout(layout: StructuralGridLayout) -> list[dict[str, Any]]:
    """Primary entry: grid definition + uniform structural_members → macro members."""
    return layout_to_macro_members(layout)


def generate_shed_from_assembly_config(config: ShedAssemblyConfig) -> list[dict[str, Any]]:
    """Legacy config → grid catalog members → resolver (no custom truss/purlin math)."""
    cfg = config.with_default_bays()
    gp = cfg.global_parameters
    grid_def = GridDefinition(
        x_spans=list(cfg.grid_layout.x_spans),
        z_spans=list(cfg.grid_layout.z_spans),
        height_mm=gp.height_mm,
        roof_pitch_deg=0.0 if gp.roof_style == "flat" else gp.roof_pitch_deg,
        roof_style=gp.roof_style,
        mono_high_side=getattr(cfg, "mono_high_side", "B"),
    )
    members = members_from_shed_config(cfg)
    layout = StructuralGridLayout(
        assembly_id=cfg.assembly_id,
        replace_existing=cfg.replace_existing,
        grid_definition=grid_def,
        structural_members=members,
    )
    return generate_shed_from_grid_layout(layout)


def generate_shed_macro(
    *,
    assembly_id: str = "shed_1",
    x_spans: list[float],
    z_spans: list[float],
    height: float,
    roof_pitch_deg: float = 10.0,
    roof_style: str = "duo_pitch",
    replace_existing: bool = True,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Legacy flat API → grid catalog (kwargs ignored except via bridge)."""
    from core.shed_config_bridge import legacy_kwargs_to_config

    config = legacy_kwargs_to_config(
        assembly_id=assembly_id,
        x_spans=x_spans,
        z_spans=z_spans,
        height=height,
        roof_pitch_deg=roof_pitch_deg,
        roof_style=roof_style,
        replace_existing=replace_existing,
        **kwargs,
    )
    return generate_shed_from_assembly_config(config)

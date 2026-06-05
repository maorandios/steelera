"""Resolve uniform structural_members against the spatial grid → macro / project elements."""

from __future__ import annotations

import math
from typing import Any

from core.engineering_rules import (
    gable_girt_center_outside_z,
    purlin_roll_deg,
    rafter_pitch_at_x,
    seat_purlin_bottom_on_rafter,
    wall_girt_center_outside_x,
)
from core.geometry_engine import macro_members_to_project_elements
from core.spatial_grid import StructuralGridEngine
from schemas.spatial_grid import StructuralGridLayout, StructuralMember

_MIN_MEMBER_LENGTH_MM = 1.0
_COLUMN_PROFILE = "HEA200"
_RAFTER_PROFILE = "IPE200"

_PROFILE_DEFAULTS: dict[str, tuple[str, str]] = {
    "column": ("HEA200", "I-beam"),
    "rafter": ("IPE200", "I-beam"),
    "truss_chord": ("IPE200", "I-beam"),
    "truss_web": ("HEA200", "I-beam"),
    "purlin": ("C150", "C-channel"),
    "wall_girt": ("C150", "C-channel"),
    "tie_beam": ("IPE200", "I-beam"),
    "bracing": ("L50x50", "Box"),
    "x_brace": ("L50x50", "Box"),
    "sag_rod": ("ROD12", "Pipe"),
}


def _macro_member(
    *,
    element_id: str,
    assembly_id: str,
    element_type: str,
    profile: str,
    position: list[float],
    rotation: list[float],
    alignment: str,
    length: float,
    axis: str,
    shape_type: str,
    nodes: dict[str, list[float]],
) -> dict[str, Any]:
    return {
        "id": element_id,
        "assembly_id": assembly_id,
        "element_type": element_type,
        "profile": profile,
        "position": position,
        "rotation": rotation,
        "alignment": alignment,
        "length": length,
        "axis": axis,
        "shape_type": shape_type,
        "nodes": nodes,
    }


def _place_secondary_steel(
    member: StructuralMember,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    grid: StructuralGridEngine,
) -> tuple[tuple[float, float, float], tuple[float, float, float], list[float], str]:
    """Seat girts/purlins outside primary steel, perpendicular to the support."""
    roof = grid.roof
    et = member.element_type
    profile = member.profile

    # Vertical sag rods belong to a WALL (they tie girts); seat them on the girt plane.
    if et == "sag_rod":
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        dz = abs(end[2] - start[2])
        if dy >= dx and dy >= dz:
            if start[0] <= 1e-6 or start[0] >= grid.total_width_mm - 1e-6:
                x_out = wall_girt_center_outside_x(
                    start[0],
                    grid.total_width_mm,
                    column_profile=_COLUMN_PROFILE,
                    girt_profile="C150",
                )
                return (
                    (x_out, start[1], start[2]),
                    (x_out, end[1], end[2]),
                    [0.0, 0.0, 0.0],
                    member.alignment,
                )
            z_out = gable_girt_center_outside_z(
                start[2],
                grid.total_length_mm,
                column_profile=_COLUMN_PROFILE,
                girt_profile="C150",
            )
            return (
                (start[0], start[1], z_out),
                (end[0], end[1], z_out),
                [0.0, 0.0, 0.0],
                member.alignment,
            )

    if et in ("purlin", "sag_rod"):
        pitch_rad, pitch_sign = rafter_pitch_at_x(
            start[0],
            style=roof.style,
            pitch_rad=roof.pitch_rad,
            ridge_x=roof.ridge_x,
            mono_high_side=roof.mono_high_side,
            is_flat=roof.is_flat,
            is_mono=roof.is_mono,
        )
        new_start = seat_purlin_bottom_on_rafter(
            *start,
            rafter_profile=_RAFTER_PROFILE,
            pitch_rad=pitch_rad,
            pitch_sign=pitch_sign,
        )
        new_end = seat_purlin_bottom_on_rafter(
            *end,
            rafter_profile=_RAFTER_PROFILE,
            pitch_rad=pitch_rad,
            pitch_sign=pitch_sign,
        )
        roll = purlin_roll_deg(pitch_rad, pitch_sign) if et == "purlin" else 0.0
        return new_start, new_end, [roll, 0.0, 0.0], "bottom"

    if et == "wall_girt":
        dx = abs(end[0] - start[0])
        dz = abs(end[2] - start[2])
        if dz >= dx:
            x_out = wall_girt_center_outside_x(
                start[0],
                grid.total_width_mm,
                column_profile=_COLUMN_PROFILE,
                girt_profile=profile,
            )
            return (
                (x_out, start[1], start[2]),
                (x_out, end[1], end[2]),
                [0.0, 0.0, 0.0],
                member.alignment,
            )
        z_out = gable_girt_center_outside_z(
            start[2],
            grid.total_length_mm,
            column_profile=_COLUMN_PROFILE,
            girt_profile=profile,
        )
        return (
            (start[0], start[1], z_out),
            (end[0], end[1], z_out),
            [0.0, 0.0, 0.0],
            member.alignment,
        )

    return start, end, [0.0, 0.0, 0.0], member.alignment


def member_from_grid_nodes(
    member: StructuralMember,
    *,
    assembly_id: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    grid: StructuralGridEngine | None = None,
) -> dict[str, Any] | None:
    profile = member.profile
    shape = _PROFILE_DEFAULTS.get(member.element_type, (profile, "I-beam"))[1]

    rotation_euler = [0.0, 0.0, 0.0]
    alignment = member.alignment
    if grid is not None and member.element_type in ("purlin", "sag_rod", "wall_girt"):
        start, end, rotation_euler, alignment = _place_secondary_steel(
            member, start, end, grid=grid
        )

    start_l = list(start)
    end_l = list(end)
    dx = end_l[0] - start_l[0]
    dy = end_l[1] - start_l[1]
    dz = end_l[2] - start_l[2]
    length = math.hypot(dx, math.hypot(dy, dz))
    if length < _MIN_MEMBER_LENGTH_MM:
        return None

    axis = "x"
    rotation = list(rotation_euler)
    if abs(dy) >= abs(dx) and abs(dy) >= abs(dz):
        axis = "y"
    elif abs(dz) >= abs(dx) and abs(dz) >= abs(dy):
        axis = "z"
    else:
        rotation = [rotation_euler[0], rotation_euler[1], math.degrees(math.atan2(dz, dx))]

    return _macro_member(
        element_id=member.id,
        assembly_id=assembly_id,
        element_type=member.element_type,
        profile=profile,
        position=start_l,
        rotation=rotation,
        alignment=alignment,
        length=length,
        axis=axis,
        shape_type=shape,
        nodes={
            "start": start_l,
            "end": end_l,
            "center": [(start_l[i] + end_l[i]) / 2 for i in range(3)],
        },
    )


def resolve_structural_members(
    grid: StructuralGridEngine,
    members: list[StructuralMember],
    *,
    assembly_id: str,
) -> list[dict[str, Any]]:
    """Iterate uniform BOM; resolve grid references → absolute mm macro members.

    Identical members (same resolved endpoints + element type) are de-duplicated so an
    over-eager AI composition can never produce overlapping steel.
    """
    macro: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for member in members:
        start = grid.resolve_node(member.start_node)
        end = grid.resolve_node(member.end_node)
        built = member_from_grid_nodes(
            member,
            assembly_id=assembly_id,
            start=start,
            end=end,
            grid=grid,
        )
        if built is None:
            continue
        a = tuple(round(c, 1) for c in built["nodes"]["start"])
        b = tuple(round(c, 1) for c in built["nodes"]["end"])
        key = (member.element_type, *sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        macro.append(built)
    return macro


def layout_to_macro_members(layout: StructuralGridLayout) -> list[dict[str, Any]]:
    from core.grid_layout_utils import ensure_layout_members

    layout = ensure_layout_members(layout)
    grid = StructuralGridEngine.from_definition(layout.grid_definition)
    return resolve_structural_members(
        grid,
        layout.structural_members,
        assembly_id=layout.assembly_id,
    )


def layout_to_project_elements(layout: StructuralGridLayout):
    return macro_members_to_project_elements(layout_to_macro_members(layout))

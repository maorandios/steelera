"""Resolve uniform structural_members against the spatial grid → macro / project elements."""

from __future__ import annotations

import math
from typing import Any

from core.engineering_rules import (
    gable_girt_center_outside_z,
    gable_girt_roll_deg,
    haunch_roll_deg,
    max_column_outside_half_on_x_line,
    max_column_outside_half_on_z_line,
    profile_column_outside_half_mm,
    purlin_ridge_mirror_flag,
    purlin_roll_deg,
    rafter_pitch_at_x,
    seat_haunch_top_on_rafter_bottom,
    seat_purlin_bottom_on_rafter,
    wall_girt_center_outside_x,
    wall_girt_roll_deg,
)
from catalog_loader import get_profile, has_profile
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
    "purlin": ("C150x2", "C-channel"),
    "wall_girt": ("C150x2", "C-channel"),
    "tie_beam": ("IPE200", "I-beam"),
    "bracing": ("L50x50", "Angle"),
    "x_brace": ("L50x50", "Angle"),
    "sag_rod": ("ROD12", "Pipe"),
    "haunch": ("IPE300", "Haunch"),
    "fly_brace": ("L50x50", "Angle"),
    "base_plate": ("PL20", "Plate"),
}

# Catalog ``shape`` field → frontend ``ShapeType``.
_CATALOG_SHAPE_TO_TYPE: dict[str, str] = {
    "I-beam": "I-beam",
    "C-channel": "C-channel",
    "Zed": "Zed",
    "RHS": "RHS",
    "SHS": "RHS",
    "CHS": "CHS",
    "Angle": "Angle",
    "Tee": "Tee",
    "Pipe": "Pipe",
    "Plate": "Plate",
    "Haunch": "Haunch",
}


def _shape_for_member(element_type: str, profile: str) -> str:
    """Resolve render shape from catalog when possible; else element-type default."""
    fallback = _PROFILE_DEFAULTS.get(element_type, (profile, "I-beam"))[1]
    if not has_profile(profile):
        return fallback
    cat_shape = str(get_profile(profile).get("shape", "")).strip()
    return _CATALOG_SHAPE_TO_TYPE.get(cat_shape, fallback)


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


def _column_profile_index(
    members: list[StructuralMember],
) -> dict[tuple[str, str], str]:
    """Map (x_axis, z_axis) grid address → column catalog profile."""
    index: dict[tuple[str, str], str] = {}
    for member in members:
        if member.element_type != "column":
            continue
        key = (member.start_node.x_axis, member.start_node.z_axis)
        index[key] = member.profile
    return index


def _side_wall_x_label(grid: StructuralGridEngine, x_mm: float) -> str:
    if x_mm <= 1e-6:
        return grid.x_labels[0]
    if x_mm >= grid.total_width_mm - 1e-6:
        return grid.x_labels[-1]
    raise ValueError(f"x={x_mm} is not on a side-wall grid line")


def _end_wall_z_label(grid: StructuralGridEngine, z_mm: float) -> str:
    if z_mm <= 1e-6:
        return grid.z_labels[0]
    if z_mm >= grid.total_length_mm - 1e-6:
        return grid.z_labels[-1]
    raise ValueError(f"z={z_mm} is not on an end-wall grid line")


def _column_outside_half_on_x_wall(
    grid: StructuralGridEngine,
    x_mm: float,
    column_profiles: dict[tuple[str, str], str],
    fallback_profile: str,
) -> float:
    try:
        x_label = _side_wall_x_label(grid, x_mm)
        return max_column_outside_half_on_x_line(x_label, column_profiles)
    except ValueError:
        return profile_column_outside_half_mm(fallback_profile)


def _column_outside_half_on_z_wall(
    grid: StructuralGridEngine,
    z_mm: float,
    column_profiles: dict[tuple[str, str], str],
    fallback_profile: str,
) -> float:
    try:
        z_label = _end_wall_z_label(grid, z_mm)
        return max_column_outside_half_on_z_line(z_label, column_profiles)
    except ValueError:
        return profile_column_outside_half_mm(fallback_profile)


def _place_secondary_steel(
    member: StructuralMember,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    grid: StructuralGridEngine,
    column_profile: str,
    column_profiles: dict[tuple[str, str], str],
    truss_chord_profile: str = _RAFTER_PROFILE,
    use_truss: bool = False,
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
                col_half = _column_outside_half_on_x_wall(
                    grid, start[0], column_profiles, column_profile
                )
                x_out = wall_girt_center_outside_x(
                    start[0],
                    grid.total_width_mm,
                    col_outside_half_mm=col_half,
                    girt_profile=profile,
                )
                return (
                    (x_out, start[1], start[2]),
                    (x_out, end[1], end[2]),
                    [0.0, 0.0, 0.0],
                    member.alignment,
                )
            col_half = _column_outside_half_on_z_wall(
                grid, start[2], column_profiles, column_profile
            )
            z_out = gable_girt_center_outside_z(
                start[2],
                grid.total_length_mm,
                col_outside_half_mm=col_half,
                girt_profile=profile,
            )
            return (
                (start[0], start[1], z_out),
                (end[0], end[1], z_out),
                [0.0, 0.0, 0.0],
                member.alignment,
            )

    if et in ("purlin", "sag_rod"):
        support_profile = truss_chord_profile if use_truss else _RAFTER_PROFILE
        if use_truss and et == "purlin":
            from core.grid_member_catalog import truss_pitch_at_x, truss_top_chord_y_at_x

            truss_type = getattr(grid.definition, "truss_type", "pratt") or "pratt"
            if str(truss_type).strip().lower() == "none":
                truss_type = "pratt"
            truss_type = str(truss_type).strip().lower()

            start = (
                start[0],
                truss_top_chord_y_at_x(grid, start[0], truss_type=truss_type),
                start[2],
            )
            end = (
                end[0],
                truss_top_chord_y_at_x(grid, end[0], truss_type=truss_type),
                end[2],
            )
            pitch_start = truss_pitch_at_x(grid, start[0], truss_type=truss_type)
            pitch_end = truss_pitch_at_x(grid, end[0], truss_type=truss_type)
            new_start = seat_purlin_bottom_on_rafter(
                *start,
                rafter_profile=support_profile,
                pitch_rad=pitch_start[0],
                pitch_sign=pitch_start[1],
            )
            new_end = seat_purlin_bottom_on_rafter(
                *end,
                rafter_profile=support_profile,
                pitch_rad=pitch_end[0],
                pitch_sign=pitch_end[1],
            )
            roll = purlin_roll_deg(pitch_start[0], pitch_start[1])
            mirror = purlin_ridge_mirror_flag(
                start[0],
                ridge_x_mm=roof.ridge_x,
                is_flat=roof.is_flat,
                is_mono=roof.is_mono,
            )
            return new_start, new_end, [roll, mirror, 0.0], "bottom"

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
            rafter_profile=support_profile,
            pitch_rad=pitch_rad,
            pitch_sign=pitch_sign,
        )
        new_end = seat_purlin_bottom_on_rafter(
            *end,
            rafter_profile=support_profile,
            pitch_rad=pitch_rad,
            pitch_sign=pitch_sign,
        )
        if et == "purlin":
            roll = purlin_roll_deg(pitch_rad, pitch_sign)
            mirror = purlin_ridge_mirror_flag(
                start[0],
                ridge_x_mm=roof.ridge_x,
                is_flat=roof.is_flat,
                is_mono=roof.is_mono,
            )
            return new_start, new_end, [roll, mirror, 0.0], "bottom"
        return new_start, new_end, [0.0, 0.0, 0.0], "bottom"

    if et == "haunch":

        def _seat_haunch(
            pt: tuple[float, float, float],
        ) -> tuple[tuple[float, float, float], float]:
            pitch_rad, pitch_sign = rafter_pitch_at_x(
                pt[0],
                style=roof.style,
                pitch_rad=roof.pitch_rad,
                ridge_x=roof.ridge_x,
                mono_high_side=roof.mono_high_side,
                is_flat=roof.is_flat,
                is_mono=roof.is_mono,
            )
            seated = seat_haunch_top_on_rafter_bottom(
                *pt,
                rafter_profile=_RAFTER_PROFILE,
                pitch_rad=pitch_rad,
                pitch_sign=pitch_sign,
            )
            return seated, pitch_sign

        new_start, _sign_start = _seat_haunch(start)
        new_end, sign_end = _seat_haunch(end)
        # Roll sign from the shallow end — unambiguous mid-slope (ridge nodes sit on
        # both sides and would pick the wrong pitch_sign from the deep end alone).
        roll = haunch_roll_deg(new_start[1], new_end[1], sign_end)
        return new_start, new_end, [roll, 0.0, 0.0], "center"

    if et == "fly_brace":
        def _fly_point(
            pt: tuple[float, float, float],
            *,
            to_purlin: bool,
        ) -> tuple[tuple[float, float, float], float]:
            pitch_rad, pitch_sign = rafter_pitch_at_x(
                pt[0],
                style=roof.style,
                pitch_rad=roof.pitch_rad,
                ridge_x=roof.ridge_x,
                mono_high_side=roof.mono_high_side,
                is_flat=roof.is_flat,
                is_mono=roof.is_mono,
            )
            if to_purlin:
                seated = seat_purlin_bottom_on_rafter(
                    *pt,
                    rafter_profile=_RAFTER_PROFILE,
                    pitch_rad=pitch_rad,
                    pitch_sign=pitch_sign,
                )
            else:
                seated = seat_haunch_top_on_rafter_bottom(
                    *pt,
                    rafter_profile=_RAFTER_PROFILE,
                    pitch_rad=pitch_rad,
                    pitch_sign=pitch_sign,
                )
            return seated, pitch_sign

        new_start, _ = _fly_point(start, to_purlin=False)
        new_end, sign_end = _fly_point(end, to_purlin=True)
        roll = haunch_roll_deg(new_start[1], new_end[1], sign_end)
        return new_start, new_end, [roll, 0.0, 0.0], "center"

    if et == "wall_girt":
        dx = abs(end[0] - start[0])
        dz = abs(end[2] - start[2])
        if dz >= dx:
            col_half = _column_outside_half_on_x_wall(
                grid, start[0], column_profiles, column_profile
            )
            x_out = wall_girt_center_outside_x(
                start[0],
                grid.total_width_mm,
                col_outside_half_mm=col_half,
                girt_profile=profile,
            )
            roll = wall_girt_roll_deg(start[0], grid.total_width_mm)
            return (
                (x_out, start[1], start[2]),
                (x_out, end[1], end[2]),
                [roll, 0.0, 0.0],
                member.alignment,
            )
        col_half = _column_outside_half_on_z_wall(
            grid, start[2], column_profiles, column_profile
        )
        z_out = gable_girt_center_outside_z(
            start[2],
            grid.total_length_mm,
            col_outside_half_mm=col_half,
            girt_profile=profile,
        )
        roll = gable_girt_roll_deg(start[2], grid.total_length_mm)
        return (
            (start[0], start[1], z_out),
            (end[0], end[1], z_out),
            [roll, 0.0, 0.0],
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
    column_profile: str = _COLUMN_PROFILE,
    column_profiles: dict[tuple[str, str], str] | None = None,
    truss_chord_profile: str = _RAFTER_PROFILE,
    use_truss: bool = False,
) -> dict[str, Any] | None:
    profile = member.profile
    shape = _shape_for_member(member.element_type, profile)

    rotation_euler = [0.0, 0.0, 0.0]
    alignment = member.alignment
    if grid is not None and member.element_type in (
        "purlin",
        "sag_rod",
        "wall_girt",
        "haunch",
        "fly_brace",
    ):
        start, end, rotation_euler, alignment = _place_secondary_steel(
            member,
            start,
            end,
            grid=grid,
            column_profile=column_profile,
            column_profiles=column_profiles or {},
            truss_chord_profile=truss_chord_profile,
            use_truss=use_truss,
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
    column_profile: str | None = None,
    truss_chord_profile: str | None = None,
) -> list[dict[str, Any]]:
    """Iterate uniform BOM; resolve grid references → absolute mm macro members.

    Identical members (same resolved endpoints + element type) are de-duplicated so an
    over-eager AI composition can never produce overlapping steel.
    """
    resolved_column = column_profile or next(
        (m.profile for m in members if m.element_type == "column"),
        _COLUMN_PROFILE,
    )
    resolved_truss_chord = truss_chord_profile or next(
        (m.profile for m in members if m.element_type == "truss_chord"),
        _RAFTER_PROFILE,
    )
    use_truss = any(m.element_type == "truss_chord" for m in members)
    column_profiles = _column_profile_index(members)
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
            column_profile=resolved_column,
            column_profiles=column_profiles,
            truss_chord_profile=resolved_truss_chord,
            use_truss=use_truss,
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
    gd = layout.grid_definition
    column_profile = getattr(gd, "column_profile", None)
    return resolve_structural_members(
        grid,
        layout.structural_members,
        assembly_id=layout.assembly_id,
        column_profile=column_profile,
    )


def layout_to_project_elements(layout: StructuralGridLayout):
    return macro_members_to_project_elements(layout_to_macro_members(layout))

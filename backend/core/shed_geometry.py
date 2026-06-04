"""
Portal-frame shed macro geometry — spans-driven layout with optional secondary steel.

Backend plan: X = width, Z = length, Y = vertical.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_MIN_MEMBER_LENGTH_MM = 1.0

from core.geometry_engine import (
    PURLIN_PROFILE,
    PURLIN_SHAPE,
    RAFTER_HALF_DEPTH_MM,
    cumulative_positions_from_spans,
    resolve_x_spans_mm,
    resolve_z_spans_mm,
)

GIRT_PROFILE = "C150"
GIRT_SHAPE = "C-channel"
TIE_PROFILE = "IPE200"
TRUSS_CHORD_PROFILE = "IPE200"
TRUSS_WEB_PROFILE = "HEA200"
BRACE_PROFILE = "L50x50"
SAG_ROD_PROFILE = "ROD12"
BRACE_SHAPE = "Box"
SAG_SHAPE = "Pipe"


@dataclass
class RoofGeometry:
    style: str
    pitch_rad: float
    ridge_x: float
    ridge_y: float
    eave_y: float
    left_span: float
    right_span: float
    left_rafter_len: float
    right_rafter_len: float
    left_pitch_deg: float
    right_pitch_deg: float

    @property
    def is_flat(self) -> bool:
        return self.style == "flat"

    @property
    def is_mono(self) -> bool:
        return self.style == "mono_pitch"


def _normalize_roof_style_and_pitch(
    roof_style: str,
    roof_pitch_deg: float,
) -> tuple[str, float]:
    """Force flat geometry when style is flat or pitch is effectively zero."""
    style = roof_style.strip().lower()
    pitch = max(0.0, float(roof_pitch_deg))
    if style == "flat" or pitch < 1e-6:
        return "flat", 0.0
    return style, pitch


def compute_roof_geometry(
    roof_style: str,
    roof_pitch_deg: float,
    total_width: float,
    eave_height: float,
) -> RoofGeometry:
    style, pitch_deg = _normalize_roof_style_and_pitch(roof_style, roof_pitch_deg)
    pitch_rad = math.radians(pitch_deg)
    eave = float(eave_height)

    if style == "flat":
        half = max(total_width / 2.0, 0.0)
        return RoofGeometry(
            style=style,
            pitch_rad=0.0,
            ridge_x=half,
            ridge_y=eave,
            eave_y=eave,
            left_span=half,
            right_span=half,
            left_rafter_len=max(total_width, 0.0),
            right_rafter_len=max(total_width, 0.0),
            left_pitch_deg=0.0,
            right_pitch_deg=0.0,
        )

    if style == "mono_pitch":
        rise = total_width * math.tan(pitch_rad)
        rafter_len = math.hypot(total_width, rise)
        pitch = math.degrees(math.atan2(rise, total_width)) if total_width > 0 else 0.0
        return RoofGeometry(
            style=style,
            pitch_rad=pitch_rad,
            ridge_x=total_width,
            ridge_y=eave + rise,
            eave_y=eave,
            left_span=total_width,
            right_span=0.0,
            left_rafter_len=rafter_len,
            right_rafter_len=0.0,
            left_pitch_deg=pitch,
            right_pitch_deg=0.0,
        )

    # duo_pitch
    ridge_x = total_width / 2.0
    left_span = ridge_x
    right_span = total_width - ridge_x
    left_rise = left_span * math.tan(pitch_rad)
    right_rise = right_span * math.tan(pitch_rad)
    left_pitch = math.degrees(math.atan2(left_rise, left_span)) if left_span > 0 else 0.0
    right_pitch = math.degrees(math.atan2(right_rise, right_span)) if right_span > 0 else 0.0
    return RoofGeometry(
        style=style,
        pitch_rad=pitch_rad,
        ridge_x=ridge_x,
        ridge_y=eave + left_rise,
        eave_y=eave,
        left_span=left_span,
        right_span=right_span,
        left_rafter_len=math.hypot(left_span, left_rise),
        right_rafter_len=math.hypot(right_span, right_rise),
        left_pitch_deg=left_pitch,
        right_pitch_deg=right_pitch,
    )


def roof_elevation_at_x(
    x: float,
    roof: RoofGeometry,
    total_width: float,
) -> float:
    if roof.is_flat:
        return roof.eave_y
    if roof.is_mono:
        return roof.eave_y + x * math.tan(roof.pitch_rad)
    if x <= roof.ridge_x + 1e-6:
        return roof.eave_y + x * math.tan(roof.pitch_rad)
    return roof.eave_y + (total_width - x) * math.tan(roof.pitch_rad)


def column_height_at_x(
    x: float,
    total_width: float,
    roof: RoofGeometry,
) -> float:
    if roof.is_mono:
        if x <= 1e-6:
            return roof.eave_y
        if x >= total_width - 1e-6:
            return roof.ridge_y
        return roof_elevation_at_x(x, roof, total_width)
    if x <= 1e-6 or x >= total_width - 1e-6:
        return roof.eave_y
    return roof_elevation_at_x(x, roof, total_width)


def _append_member(
    members: list[dict[str, Any]],
    member: dict[str, Any] | None,
) -> None:
    if member is not None:
        members.append(member)


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
    shape_type: str | None = None,
    nodes: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    return {
        "id": element_id,
        "assembly_id": assembly_id,
        "element_type": element_type,
        "profile": profile,
        "position": [float(position[0]), float(position[1]), float(position[2])],
        "rotation": [float(rotation[0]), float(rotation[1]), float(rotation[2])],
        "alignment": alignment,
        "length": float(length),
        "axis": axis,
        "shape_type": shape_type,
        "nodes": nodes,
    }


def _member_along_axis(
    start: list[float],
    end: list[float],
    *,
    element_id: str,
    assembly_id: str,
    element_type: str,
    profile: str,
    shape_type: str,
    alignment: str = "center",
    extra_rotation: list[float] | None = None,
) -> dict[str, Any] | None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.hypot(dx, math.hypot(dy, dz))
    if length < _MIN_MEMBER_LENGTH_MM:
        return None
    axis = "x"
    rotation = [0.0, 0.0, 0.0]
    if abs(dy) >= abs(dx) and abs(dy) >= abs(dz):
        axis = "y"
    elif abs(dz) >= abs(dx) and abs(dz) >= abs(dy):
        axis = "z"
    else:
        rotation = [0.0, 0.0, math.degrees(math.atan2(dz, dx))]
    if extra_rotation:
        rotation = [
            rotation[0] + extra_rotation[0],
            rotation[1] + extra_rotation[1],
            rotation[2] + extra_rotation[2],
        ]
    return _macro_member(
        element_id=element_id,
        assembly_id=assembly_id,
        element_type=element_type,
        profile=profile,
        position=start,
        rotation=rotation,
        alignment=alignment,
        length=length,
        axis=axis,
        shape_type=shape_type,
        nodes={"start": start, "end": end, "center": [(start[i] + end[i]) / 2 for i in range(3)]},
    )


def _generate_columns(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    x_positions: list[float],
    frame_zs: list[float],
    total_width: float,
    roof: RoofGeometry,
) -> None:
    for frame_index, z in enumerate(frame_zs):
        for x_index, x in enumerate(x_positions):
            col_h = column_height_at_x(x, total_width, roof)
            members.append(
                _macro_member(
                    element_id=f"shed-col-{frame_index}-{x_index}",
                    assembly_id=assembly_id,
                    element_type="column",
                    profile="HEA200",
                    position=[x, 0.0, z],
                    rotation=[0.0, 0.0, 0.0],
                    alignment="center",
                    length=col_h,
                    axis="y",
                    shape_type="I-beam",
                    nodes={
                        "bottom": [x, 0.0, z],
                        "top": [x, col_h, z],
                        "center": [x, col_h * 0.5, z],
                    },
                )
            )


def _generate_solid_rafters(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    frame_index: int,
    z: float,
    total_width: float,
    roof: RoofGeometry,
) -> None:
    eave_y = roof.eave_y
    if roof.is_flat:
        m = _member_along_axis(
            [0.0, eave_y, z],
            [total_width, eave_y, z],
            element_id=f"shed-raf-{frame_index}",
            assembly_id=assembly_id,
            element_type="rafter",
            profile="IPE200",
            shape_type="I-beam",
        )
        if m:
            members.append(m)
        return

    if roof.is_mono:
        m = _member_along_axis(
            [0.0, eave_y, z],
            [roof.ridge_x, roof.ridge_y, z],
            element_id=f"shed-raf-{frame_index}",
            assembly_id=assembly_id,
            element_type="rafter",
            profile="IPE200",
            shape_type="I-beam",
            extra_rotation=[0.0, 0.0, roof.left_pitch_deg],
        )
        if m:
            members.append(m)
        return

    for element_id, x_end, extra_rot in (
        (f"shed-raf-L-{frame_index}", roof.ridge_x, [0.0, 0.0, roof.left_pitch_deg]),
        (
            f"shed-raf-R-{frame_index}",
            roof.ridge_x,
            [0.0, 0.0, 180.0 - roof.right_pitch_deg],
        ),
    ):
        x_start = 0.0 if element_id.startswith("shed-raf-L") else total_width
        m = _member_along_axis(
            [x_start, eave_y, z],
            [x_end, roof.ridge_y, z],
            element_id=element_id,
            assembly_id=assembly_id,
            element_type="rafter",
            profile="IPE200",
            shape_type="I-beam",
            extra_rotation=extra_rot,
        )
        if m:
            members.append(m)


def _generate_truss_half(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    frame_index: int,
    z: float,
    x0: float,
    x1: float,
    bottom_y0: float,
    bottom_y1: float,
    top_y0: float,
    top_y1: float,
    suffix: str,
    panels: int = 4,
    mirror_pratt: bool = False,
) -> None:
    """
    Pratt half-truss from x0→x1.
    Bottom/top chord elevations are specified independently at each end
    (supports symmetrical duo-pitch left/right halves meeting at the ridge).
    mirror_pratt flips web diagonal handedness for the right-hand half.
    """
    panel_dx = (x1 - x0) / panels
    bottom: list[list[float]] = []
    top: list[list[float]] = []
    for i in range(panels + 1):
        t = i / panels
        x = x0 + panel_dx * i
        bottom.append(
            [x, bottom_y0 + (bottom_y1 - bottom_y0) * t, z],
        )
        top.append(
            [x, top_y0 + (top_y1 - top_y0) * t, z],
        )

    _append_member(
        members,
        _member_along_axis(
            bottom[0],
            bottom[-1],
            element_id=f"shed-truss-bot-{suffix}-{frame_index}",
            assembly_id=assembly_id,
            element_type="truss_chord",
            profile=TRUSS_CHORD_PROFILE,
            shape_type="I-beam",
        ),
    )
    _append_member(
        members,
        _member_along_axis(
            top[0],
            top[-1],
            element_id=f"shed-truss-top-{suffix}-{frame_index}",
            assembly_id=assembly_id,
            element_type="truss_chord",
            profile=TRUSS_CHORD_PROFILE,
            shape_type="I-beam",
        ),
    )

    # Pratt webs progress in +X (left half) or +X from ridge (right half, mirrored).
    for i in range(panels):
        if mirror_pratt:
            if i % 2 == 0:
                web_start, web_end = bottom[i + 1], top[i + 1]
                web_kind = "v"
            else:
                web_start, web_end = bottom[i], top[i + 1]
                web_kind = "d"
        else:
            if i % 2 == 0:
                web_start, web_end = bottom[i], top[i + 1]
                web_kind = "d"
            else:
                web_start, web_end = bottom[i + 1], top[i + 1]
                web_kind = "v"
        _append_member(
            members,
            _member_along_axis(
                web_start,
                web_end,
                element_id=f"shed-truss-web-{web_kind}-{suffix}-{frame_index}-{i}",
                assembly_id=assembly_id,
                element_type="truss_web",
                profile=TRUSS_WEB_PROFILE,
                shape_type="I-beam",
            ),
        )


def _generate_trusses(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    frame_zs: list[float],
    total_width: float,
    roof: RoofGeometry,
) -> None:
    for frame_index, z in enumerate(frame_zs):
        eave_y = roof.eave_y
        if roof.is_flat:
            _generate_truss_half(
                members,
                assembly_id=assembly_id,
                frame_index=frame_index,
                z=z,
                x0=0.0,
                x1=total_width,
                bottom_y0=eave_y,
                bottom_y1=eave_y,
                top_y0=eave_y,
                top_y1=eave_y,
                suffix="flat",
                panels=6,
            )
        elif roof.is_mono:
            _generate_truss_half(
                members,
                assembly_id=assembly_id,
                frame_index=frame_index,
                z=z,
                x0=0.0,
                x1=roof.ridge_x,
                bottom_y0=eave_y,
                bottom_y1=eave_y,
                top_y0=eave_y,
                top_y1=roof.ridge_y,
                suffix="mono",
                panels=5,
            )
        else:
            # Duo-pitch: two mirrored Pratt halves; shared ridge node, no overlap.
            half_panels = max(3, min(6, int(max(roof.left_span, roof.right_span) / 2500)))
            _generate_truss_half(
                members,
                assembly_id=assembly_id,
                frame_index=frame_index,
                z=z,
                x0=0.0,
                x1=roof.ridge_x,
                bottom_y0=eave_y,
                bottom_y1=eave_y,
                top_y0=eave_y,
                top_y1=roof.ridge_y,
                suffix="L",
                panels=half_panels,
                mirror_pratt=False,
            )
            _generate_truss_half(
                members,
                assembly_id=assembly_id,
                frame_index=frame_index,
                z=z,
                x0=roof.ridge_x,
                x1=total_width,
                bottom_y0=eave_y,
                bottom_y1=eave_y,
                top_y0=roof.ridge_y,
                top_y1=eave_y,
                suffix="R",
                panels=half_panels,
                mirror_pratt=True,
            )


def _generate_purlins(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    first_frame_z: float,
    last_frame_z: float,
    purlin_spacing: float,
    total_width: float,
    height: float,
    roof: RoofGeometry,
) -> None:
    purlin_index = 0

    def place_slope(
        suffix: str,
        rafter_len: float,
        pitch_deg: float,
        pitch_sign: float,
        x_eave: float,
        x_peak: float,
    ) -> None:
        nonlocal purlin_index
        if rafter_len < 1e-6:
            return
        slope_rad = math.radians(pitch_deg)
        slope_pos = 0.0
        while slope_pos <= rafter_len + 1e-6:
            t = slope_pos / rafter_len
            x_pos = x_eave + (x_peak - x_eave) * t
            if roof.is_flat:
                elev_y = roof.eave_y
            else:
                elev_y = height + slope_pos * math.sin(slope_rad)
            normal_x = -math.sin(slope_rad) * pitch_sign
            normal_y = math.cos(slope_rad)
            seat_x = x_pos + RAFTER_HALF_DEPTH_MM * normal_x
            seat_y = elev_y + RAFTER_HALF_DEPTH_MM * normal_y
            run = last_frame_z - first_frame_z
            members.append(
                _macro_member(
                    element_id=f"shed-purl-{suffix}-{purlin_index}",
                    assembly_id=assembly_id,
                    element_type="purlin",
                    profile=PURLIN_PROFILE,
                    position=[seat_x, seat_y, first_frame_z],
                    rotation=[pitch_sign * pitch_deg, 0.0, 0.0],
                    alignment="bottom",
                    length=run,
                    axis="z",
                    shape_type=PURLIN_SHAPE,
                    nodes={
                        "start": [seat_x, seat_y, first_frame_z],
                        "end": [seat_x, seat_y, last_frame_z],
                        "center": [seat_x, seat_y, first_frame_z + run * 0.5],
                    },
                )
            )
            if slope_pos >= rafter_len - 1e-6:
                break
            slope_pos += purlin_spacing
            purlin_index += 1

    if roof.is_flat:
        place_slope("F", total_width, 0.0, 0.0, 0.0, total_width)
    elif roof.is_mono:
        place_slope("M", roof.left_rafter_len, roof.left_pitch_deg, 1.0, 0.0, roof.ridge_x)
    else:
        place_slope("L", roof.left_rafter_len, roof.left_pitch_deg, 1.0, 0.0, roof.ridge_x)
        place_slope("R", roof.right_rafter_len, roof.right_pitch_deg, -1.0, total_width, roof.ridge_x)


def _girt_levels_for_wall(max_y: float, spacing: float) -> list[float]:
    """Vertical girt lines strictly below the local wall/column envelope (mm)."""
    if max_y < spacing - 1e-6:
        return []
    levels: list[float] = []
    y = spacing
    while y < max_y - 1e-6:
        levels.append(round(y, 3))
        y += spacing
    # Flush top girt at column/roof line when the last spaced level sits below it.
    if not levels or levels[-1] < max_y - spacing * 0.25:
        levels.append(round(max_y, 3))
    return levels


def _generate_wall_girts(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    x_positions: list[float],
    frame_zs: list[float],
    total_width: float,
    total_length: float,
    roof: RoofGeometry,
    girt_spacing: float,
) -> None:
    girt_index = 0

    # Longitudinal side walls (along Z) at X = 0 and X = total_width.
    for side, x in enumerate((0.0, total_width)):
        wall_max_y = column_height_at_x(x, total_width, roof)
        for level_y in _girt_levels_for_wall(wall_max_y, girt_spacing):
            members.append(
                _macro_member(
                    element_id=f"shed-girt-L{side}-{girt_index}",
                    assembly_id=assembly_id,
                    element_type="wall_girt",
                    profile=GIRT_PROFILE,
                    position=[x, level_y, 0.0],
                    rotation=[0.0, 0.0, 0.0],
                    alignment="center",
                    length=total_length,
                    axis="z",
                    shape_type=GIRT_SHAPE,
                    nodes={
                        "start": [x, level_y, 0.0],
                        "end": [x, level_y, total_length],
                        "center": [x, level_y, total_length * 0.5],
                    },
                )
            )
            girt_index += 1

    # Gable end walls (along X): segment between column lines; Y clipped to both column tops.
    for side, z in enumerate((0.0, total_length)):
        for x_i in range(len(x_positions) - 1):
            xa = x_positions[x_i]
            xb = x_positions[x_i + 1]
            segment_max_y = min(
                column_height_at_x(xa, total_width, roof),
                column_height_at_x(xb, total_width, roof),
            )
            for level_y in _girt_levels_for_wall(segment_max_y, girt_spacing):
                span = xb - xa
                members.append(
                    _macro_member(
                        element_id=f"shed-girt-T{side}-{x_i}-{girt_index}",
                        assembly_id=assembly_id,
                        element_type="wall_girt",
                        profile=GIRT_PROFILE,
                        position=[xa, level_y, z],
                        rotation=[0.0, 0.0, 0.0],
                        alignment="center",
                        length=span,
                        axis="x",
                        shape_type=GIRT_SHAPE,
                        nodes={
                            "start": [xa, level_y, z],
                            "end": [xb, level_y, z],
                            "center": [xa + span * 0.5, level_y, z],
                        },
                    )
                )
                girt_index += 1


def _generate_tie_beams(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    x_positions: list[float],
    frame_zs: list[float],
    total_width: float,
    roof: RoofGeometry,
) -> None:
    if len(frame_zs) < 2:
        return
    for x_index, x in enumerate(x_positions):
        eave_y = roof.eave_y
        for tie_index in range(len(frame_zs) - 1):
            z0 = frame_zs[tie_index]
            z1 = frame_zs[tie_index + 1]
            span = z1 - z0
            # Eave tie
            members.append(
                _macro_member(
                    element_id=f"shed-tie-eave-{x_index}-{tie_index}",
                    assembly_id=assembly_id,
                    element_type="tie_beam",
                    profile=TIE_PROFILE,
                    position=[x, eave_y, z0],
                    rotation=[0.0, 0.0, 0.0],
                    alignment="center",
                    length=span,
                    axis="z",
                    shape_type="I-beam",
                    nodes={
                        "start": [x, eave_y, z0],
                        "end": [x, eave_y, z1],
                        "center": [x, eave_y, (z0 + z1) * 0.5],
                    },
                )
            )
            # Ridge / high-side tie
            ridge_y = roof_elevation_at_x(x, roof, total_width)
            if abs(ridge_y - eave_y) > 50:
                members.append(
                    _macro_member(
                        element_id=f"shed-tie-ridge-{x_index}-{tie_index}",
                        assembly_id=assembly_id,
                        element_type="tie_beam",
                        profile=TIE_PROFILE,
                        position=[x, ridge_y, z0],
                        rotation=[0.0, 0.0, 0.0],
                        alignment="center",
                        length=span,
                        axis="z",
                        shape_type="I-beam",
                        nodes={
                            "start": [x, ridge_y, z0],
                            "end": [x, ridge_y, z1],
                            "center": [x, ridge_y, (z0 + z1) * 0.5],
                        },
                    )
                )


def _generate_bracing(
    members: list[dict[str, Any]],
    *,
    assembly_id: str,
    x_positions: list[float],
    frame_zs: list[float],
    total_width: float,
    roof: RoofGeometry,
) -> None:
    if len(frame_zs) < 2:
        return
    brace_idx = 0

    # Wall X-bracing on longitudinal SIDE walls (X = 0 and X = total_width),
    # in the FIRST and LAST Z bays only — column base to column top per diagonal.
    side_wall_xs = (0.0, total_width)
    end_bay_indices = [0, len(frame_zs) - 2]

    for bay_i in end_bay_indices:
        z0 = frame_zs[bay_i]
        z1 = frame_zs[bay_i + 1]
        for x in side_wall_xs:
            col_top = column_height_at_x(x, total_width, roof)
            _append_member(
                members,
                _member_along_axis(
                    [x, 0.0, z0],
                    [x, col_top, z1],
                    element_id=f"shed-brace-wall-{brace_idx}",
                    assembly_id=assembly_id,
                    element_type="bracing",
                    profile=BRACE_PROFILE,
                    shape_type=BRACE_SHAPE,
                ),
            )
            _append_member(
                members,
                _member_along_axis(
                    [x, col_top, z0],
                    [x, 0.0, z1],
                    element_id=f"shed-brace-wall-{brace_idx + 1}",
                    assembly_id=assembly_id,
                    element_type="bracing",
                    profile=BRACE_PROFILE,
                    shape_type=BRACE_SHAPE,
                ),
            )
            brace_idx += 2

    # Roof bracing between frames at eave level (first/last Z bay)
    for bay in (0, len(frame_zs) - 2):
        z0, z1 = frame_zs[bay], frame_zs[bay + 1]
        for x in (0.0, total_width):
            y_eave = roof.eave_y + 200
            y_ridge = roof_elevation_at_x(x, roof, total_width) - 200
            _append_member(
                members,
                _member_along_axis(
                    [x, y_eave, z0],
                    [x, y_ridge, z1],
                    element_id=f"shed-brace-roof-{brace_idx}",
                    assembly_id=assembly_id,
                    element_type="bracing",
                    profile=BRACE_PROFILE,
                    shape_type=BRACE_SHAPE,
                ),
            )
            _append_member(
                members,
                _member_along_axis(
                    [x, y_ridge, z0],
                    [x, y_eave, z1],
                    element_id=f"shed-brace-roof-{brace_idx + 1}",
                    assembly_id=assembly_id,
                    element_type="bracing",
                    profile=BRACE_PROFILE,
                    shape_type=BRACE_SHAPE,
                ),
            )
            brace_idx += 2


def _purlin_slope_suffix(member: dict[str, Any]) -> str:
    parts = str(member.get("id", "")).split("-")
    return parts[2] if len(parts) > 2 else ""


def _generate_sag_rods(
    members: list[dict[str, Any]],
    *,
    purlin_members: list[dict[str, Any]],
    girt_members: list[dict[str, Any]],
    frame_zs: list[float],
) -> None:
    """
    Sag rods at the mid-span of each Z bay (not on portal-frame grid lines).
    Tie neighboring purlins (along roof slope) and vertical pairs of side-wall girts.
    """
    sag_idx = 0
    if len(frame_zs) < 2:
        return

    def _purlin_sort_key(m: dict[str, Any]) -> tuple[str, float]:
        return (_purlin_slope_suffix(m), float(m["position"][0]))

    sorted_purlins = sorted(purlin_members, key=_purlin_sort_key)
    by_slope: dict[str, list[dict[str, Any]]] = {}
    for purlin in sorted_purlins:
        suffix = _purlin_slope_suffix(purlin)
        by_slope.setdefault(suffix, []).append(purlin)

    # One sag rod per Z-bay per roof slope (mid purlin gap) — avoids hundreds of ties.
    for bay_i in range(len(frame_zs) - 1):
        z_center = (frame_zs[bay_i] + frame_zs[bay_i + 1]) * 0.5
        for suffix, slope_purlins in by_slope.items():
            if len(slope_purlins) < 2:
                continue
            mid = len(slope_purlins) // 2
            a, b = slope_purlins[mid - 1], slope_purlins[mid]
            pa, pb = a["position"], b["position"]
            _append_member(
                members,
                _member_along_axis(
                    [pa[0], pa[1], z_center],
                    [pb[0], pb[1], z_center],
                    element_id=f"shed-sag-purl-{suffix}-b{bay_i}",
                    assembly_id=a["assembly_id"],
                    element_type="sag_rod",
                    profile=SAG_ROD_PROFILE,
                    shape_type=SAG_SHAPE,
                ),
            )
            sag_idx += 1


def _is_bad_number(value: float) -> bool:
    return not math.isfinite(value)


def _clean_scalar(value: float, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return fallback if _is_bad_number(number) else number


def _clean_vec3(
    coords: list[float] | tuple[float, ...] | None,
    fallback: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> list[float]:
    if not coords or len(coords) < 3:
        return list(fallback)
    return [
        _clean_scalar(coords[0], fallback[0]),
        _clean_scalar(coords[1], fallback[1]),
        _clean_scalar(coords[2], fallback[2]),
    ]


def _sanitize_macro_member(member: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Replace NaN/Inf with safe values; return warnings for logging."""
    warnings: list[str] = []
    pos_fb = (0.0, 0.0, 0.0)
    position = _clean_vec3(member.get("position"), pos_fb)
    rotation_raw = member.get("rotation") or [0.0, 0.0, 0.0]
    rotation = _clean_vec3(
        list(rotation_raw) if isinstance(rotation_raw, (list, tuple)) else [0.0, 0.0, 0.0],
    )
    length = _clean_scalar(float(member.get("length", 0.0)), 0.0)

    nodes_out: dict[str, list[float]] | None = None
    raw_nodes = member.get("nodes")
    if isinstance(raw_nodes, dict):
        nodes_out = {}
        for key, coords in raw_nodes.items():
            cleaned = _clean_vec3(
                list(coords) if isinstance(coords, (list, tuple)) else None,
                tuple(position),
            )
            if raw_nodes.get(key) != cleaned:
                warnings.append(f"nodes.{key}")
            nodes_out[key] = cleaned

    if nodes_out and "start" in nodes_out and "end" in nodes_out:
        start = nodes_out["start"]
        end = nodes_out["end"]
        length = math.hypot(
            end[0] - start[0],
            math.hypot(end[1] - start[1], end[2] - start[2]),
        )
        position = [(start[i] + end[i]) * 0.5 for i in range(3)]
    elif nodes_out and "bottom" in nodes_out and "top" in nodes_out:
        bottom = nodes_out["bottom"]
        top = nodes_out["top"]
        length = math.hypot(
            top[0] - bottom[0],
            math.hypot(top[1] - bottom[1], top[2] - bottom[2]),
        )
        position = [(bottom[i] + top[i]) * 0.5 for i in range(3)]

    if _is_bad_number(length):
        warnings.append("length")
        length = 0.0

    cleaned = {
        **member,
        "position": position,
        "rotation": rotation,
        "length": length,
        "nodes": nodes_out if nodes_out else member.get("nodes"),
    }
    return cleaned, warnings


def _sanitize_macro_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for member in members:
        cleaned, issues = _sanitize_macro_member(member)
        if issues:
            logger.warning(
                "Sanitized shed member %s (%s): replaced non-finite fields",
                cleaned.get("id", "?"),
                ", ".join(issues),
            )
        if cleaned.get("length", 0.0) >= _MIN_MEMBER_LENGTH_MM:
            sanitized.append(cleaned)
        else:
            logger.warning(
                "Dropped shed member %s: length below minimum (%.3f mm)",
                cleaned.get("id", "?"),
                cleaned.get("length", 0.0),
            )
    return sanitized


def generate_shed_macro(
    assembly_id: str,
    height: float,
    roof_pitch_deg: float = 10.0,
    purlin_spacing: float = 1200.0,
    *,
    x_spans: list[float] | str,
    z_spans: list[float] | str,
    roof_style: str = "duo_pitch",
    use_truss: bool = False,
    use_bracing: bool = False,
    use_sag_rods: bool = False,
    generate_wall_girts: bool = True,
    generate_tie_beams: bool = True,
    girt_spacing_mm: float = 1500.0,
    width: float | None = None,
    length: float | None = None,
    frame_spacing: float | None = None,
) -> list[dict[str, Any]]:
    """
    Full industrial portal-frame shed macro (mm).

    Spans drive portal frame grid; optional trusses, girts, ties, bracing, sag rods.
    """
    x_span_list = resolve_x_spans_mm(x_spans=x_spans, width=width)
    z_span_list = resolve_z_spans_mm(
        z_spans=z_spans, length=length, frame_spacing=frame_spacing
    )
    x_positions = cumulative_positions_from_spans(x_span_list)
    frame_zs = cumulative_positions_from_spans(z_span_list)
    total_width = x_positions[-1]
    total_length = frame_zs[-1]

    if total_width <= 0 or total_length <= 0 or height <= 0:
        raise ValueError("total width, total length, and height must be positive")
    if purlin_spacing <= 0 or girt_spacing_mm <= 0:
        raise ValueError("purlin_spacing and girt_spacing_mm must be positive")

    norm_style, norm_pitch = _normalize_roof_style_and_pitch(
        roof_style, roof_pitch_deg
    )
    roof = compute_roof_geometry(norm_style, norm_pitch, total_width, height)
    members: list[dict[str, Any]] = []
    first_z = frame_zs[0]
    last_z = frame_zs[-1]

    _generate_columns(
        members,
        assembly_id=assembly_id,
        x_positions=x_positions,
        frame_zs=frame_zs,
        total_width=total_width,
        roof=roof,
    )

    if use_truss:
        _generate_trusses(
            members,
            assembly_id=assembly_id,
            frame_zs=frame_zs,
            total_width=total_width,
            roof=roof,
        )
    else:
        for frame_index, z in enumerate(frame_zs):
            _generate_solid_rafters(
                members,
                assembly_id=assembly_id,
                frame_index=frame_index,
                z=z,
                total_width=total_width,
                roof=roof,
            )

    _generate_purlins(
        members,
        assembly_id=assembly_id,
        first_frame_z=first_z,
        last_frame_z=last_z,
        purlin_spacing=purlin_spacing,
        total_width=total_width,
        height=height,
        roof=roof,
    )

    girt_members: list[dict[str, Any]] = []
    if generate_wall_girts:
        before = len(members)
        _generate_wall_girts(
            members,
            assembly_id=assembly_id,
            x_positions=x_positions,
            frame_zs=frame_zs,
            total_width=total_width,
            total_length=total_length,
            roof=roof,
            girt_spacing=girt_spacing_mm,
        )
        girt_members = members[before:]

    if generate_tie_beams:
        _generate_tie_beams(
            members,
            assembly_id=assembly_id,
            x_positions=x_positions,
            frame_zs=frame_zs,
            total_width=total_width,
            roof=roof,
        )

    if use_bracing:
        _generate_bracing(
            members,
            assembly_id=assembly_id,
            x_positions=x_positions,
            frame_zs=frame_zs,
            total_width=total_width,
            roof=roof,
        )

    if use_sag_rods:
        purlin_members = [m for m in members if m.get("element_type") == "purlin"]
        _generate_sag_rods(
            members,
            purlin_members=purlin_members,
            girt_members=girt_members,
            frame_zs=frame_zs,
        )

    return _sanitize_macro_members(members)

"""
Structural engineering rules for portal-frame shed generation.

Aligned with Eurocode 3 (EN 1993) detailing practice and Israeli Standard 1225
(steel structures) for bracing, anti-sag systems, and truss web layouts.

The AI assistant orchestrates layout intent; this module enforces millimetric,
code-aware geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from catalog_loader import get_profile

# EC3 / IS 1225: typical truss web angles for shear transfer
WEB_ANGLE_MIN_DEG = 30.0
WEB_ANGLE_MAX_DEG = 60.0
WEB_ANGLE_TARGET_DEG = 45.0

# Anti-sag: single row in short bays; dual rows in wide bays (LTB control)
SAG_BAY_SINGLE_ROW_MAX_MM = 5500.0


@dataclass(frozen=True)
class PrattWebMember:
    """One Pratt truss web diagonal or vertical strut."""

    start: tuple[float, float, float]
    end: tuple[float, float, float]
    kind: Literal["d", "v"]


@dataclass(frozen=True)
class PrattTrussLayout:
    """Panelized Pratt half-truss node grid and web members."""

    panels: int
    bottom_nodes: list[tuple[float, float, float]]
    top_nodes: list[tuple[float, float, float]]
    webs: list[PrattWebMember]


@dataclass(frozen=True)
class TieBeamSpec:
    """Longitudinal tie at a column–rafter junction between two frames."""

    x: float
    y: float
    z0: float
    z1: float
    level: Literal["eave", "ridge"]


def profile_half_depth_mm(profile_name: str) -> float:
    """Distance from section centerline to outer flange (mm)."""
    section = get_profile(profile_name)
    return float(section["h"]) / 2.0


def profile_half_width_mm(profile_name: str) -> float:
    """Half flange width — offsets wall girts/bracing from column centerline (mm)."""
    section = get_profile(profile_name)
    return float(section["b"]) / 2.0


def profile_column_outside_half_mm(profile_name: str) -> float:
    """Half extent from column centre to its outer face (max of h/b) for girt flush."""
    section = get_profile(profile_name)
    return max(float(section["h"]), float(section["b"])) / 2.0


def max_column_outside_half_on_x_line(
    x_label: str,
    column_profiles: dict[tuple[str, str], str],
) -> float:
    """Largest column half-face among every column on an X grid line."""
    halves = [
        profile_column_outside_half_mm(prof)
        for (xl, _zl), prof in column_profiles.items()
        if xl == x_label
    ]
    if not halves:
        raise ValueError(f"no columns found on x grid line '{x_label}'")
    return max(halves)


def max_column_outside_half_on_z_line(
    z_label: str,
    column_profiles: dict[tuple[str, str], str],
) -> float:
    """Largest column half-face among every column on a Z grid line."""
    halves = [
        profile_column_outside_half_mm(prof)
        for (_xl, zl), prof in column_profiles.items()
        if zl == z_label
    ]
    if not halves:
        raise ValueError(f"no columns found on z grid line '{z_label}'")
    return max(halves)


def _rafter_outward_normal(pitch_rad: float, pitch_sign: float) -> tuple[float, float]:
    """Unit normal from rafter centerline to top flange (outward / upward)."""
    return (-math.sin(pitch_rad) * pitch_sign, math.cos(pitch_rad))


def rafter_pitch_at_x(
    x_mm: float,
    *,
    style: str,
    pitch_rad: float,
    ridge_x: float,
    mono_high_side: str,
    is_flat: bool,
    is_mono: bool,
) -> tuple[float, float]:
    """Return (pitch_rad, pitch_sign) for the rafter supporting purlins at x_mm."""
    if is_flat or pitch_rad < 1e-9:
        return 0.0, 1.0
    if is_mono:
        if str(mono_high_side).strip().upper() == "A":
            return pitch_rad, -1.0
        return pitch_rad, 1.0
    if x_mm <= ridge_x + 1e-6:
        return pitch_rad, 1.0
    return pitch_rad, -1.0


def seat_on_top_flange(
    x: float,
    y_centerline: float,
    z: float,
    *,
    rafter_profile: str,
    pitch_rad: float,
    pitch_sign: float = 1.0,
) -> tuple[float, float, float]:
    """Purlin / sag seat on top flange of sloping rafter (not centerline)."""
    half = profile_half_depth_mm(rafter_profile)
    normal_x, normal_y = _rafter_outward_normal(pitch_rad, pitch_sign)
    return (
        x + half * normal_x,
        y_centerline + half * normal_y,
        z,
    )


def seat_purlin_bottom_on_rafter(
    x: float,
    y_centerline: float,
    z: float,
    *,
    rafter_profile: str,
    pitch_rad: float,
    pitch_sign: float = 1.0,
) -> tuple[float, float, float]:
    """Bottom-of-purlin node on rafter top flange (use with alignment=bottom)."""
    return seat_on_top_flange(
        x,
        y_centerline,
        z,
        rafter_profile=rafter_profile,
        pitch_rad=pitch_rad,
        pitch_sign=pitch_sign,
    )


def seat_haunch_top_on_rafter_bottom(
    x: float,
    y_centerline: float,
    z: float,
    *,
    rafter_profile: str,
    pitch_rad: float,
    pitch_sign: float = 1.0,
) -> tuple[float, float, float]:
    """Top-of-haunch node on rafter bottom flange (use with top-aligned Haunch mesh)."""
    half = profile_half_depth_mm(rafter_profile)
    nx, ny = _rafter_outward_normal(pitch_rad, pitch_sign)
    return (
        x - half * nx,
        y_centerline - half * ny,
        z,
    )


def haunch_roll_deg(
    start_y_mm: float,
    end_y_mm: float,
    pitch_sign: float,
) -> float:
    """Roll about member +X so local -Y hangs toward the rafter bottom flange.

    ``setFromUnitVectors`` picks opposite cross-section orientations for uphill
    vs downhill runs; flip 180° when climb direction and pitch_sign disagree.
    """
    climbing = end_y_mm > start_y_mm + 1e-6
    uphill_side = pitch_sign > 0
    return 180.0 if climbing != uphill_side else 0.0


def purlin_roll_deg(pitch_rad: float, pitch_sign: float) -> float:
    """Roll C-channel lips vertical to the roof plane (90° to rafter)."""
    return math.degrees(pitch_rad) * pitch_sign


def purlin_ridge_mirror_flag(
    x_mm: float,
    *,
    ridge_x_mm: float,
    is_flat: bool,
    is_mono: bool,
) -> float:
    """Non-zero Y-Euler sentinel so the renderer mirrors the C-profile across the ridge."""
    if is_flat or is_mono:
        return 0.0
    return 180.0 if x_mm > ridge_x_mm + 1e-6 else 0.0


# Ridge-adjacent purlin sits this far from the apex along the slope (when added).
PURLIN_APEX_CLEARANCE_MM = 100.0
# Only add that purlin when the last spaced bay to the apex exceeds this (mm).
PURLIN_APEX_MIN_GAP_MM = 300.0
# Matches member_resolver seating (IPE200 top flange).
PURLIN_SEAT_RAFTER_PROFILE = "IPE200"


def purlin_seat_slope_offset_mm(
    pitch_rad: float,
    rafter_profile: str = PURLIN_SEAT_RAFTER_PROFILE,
) -> float:
    """Centerline-to-seated-bottom offset measured along the rafter (mm)."""
    if pitch_rad < 1e-9:
        return 0.0
    return profile_half_depth_mm(rafter_profile) * math.tan(pitch_rad)


def purlin_distances_along_slope_mm(
    slope_length_mm: float,
    spacing_mm: float,
    *,
    apex_clearance_mm: float = PURLIN_APEX_CLEARANCE_MM,
    apex_min_gap_mm: float = PURLIN_APEX_MIN_GAP_MM,
    pitch_rad: float = 0.0,
    rafter_profile: str = PURLIN_SEAT_RAFTER_PROFILE,
) -> list[float]:
    """Distances along a rafter from the eave, including the eave at 0.

    Spacing is measured along the rafter. When the gap from the last spaced
    purlin to the apex exceeds ``apex_min_gap_mm``, an extra purlin is added
    with its seated bottom ``apex_clearance_mm`` from the apex.
    """
    if slope_length_mm <= 0 or spacing_mm <= 0:
        return [0.0] if slope_length_mm > 0 else []
    # Seated bottom sits h·tan(p) toward the eave from centerline along the slope.
    seat_offset = purlin_seat_slope_offset_mm(pitch_rad, rafter_profile)
    apex_dist = slope_length_mm - apex_clearance_mm + seat_offset
    if apex_dist <= 1e-6:
        return [0.0]
    distances = [0.0]
    d = spacing_mm
    while d < apex_dist - 1e-6:
        distances.append(d)
        d += spacing_mm
    gap_to_apex = slope_length_mm - distances[-1]
    if gap_to_apex > apex_min_gap_mm + 1e-6 and abs(distances[-1] - apex_dist) > 1e-6:
        distances.append(apex_dist)
    return distances


def _slope_distances_to_x_mm(
    eave_x_mm: float,
    toward_ridge: bool,
    distances_mm: list[float],
    pitch_rad: float,
) -> list[float]:
    """Map slope distances from an eave to absolute X coordinates."""
    if not distances_mm:
        return []
    cos_p = math.cos(pitch_rad)
    step = cos_p if toward_ridge else -cos_p
    return [eave_x_mm + d * step for d in distances_mm]


def duo_pitch_purlin_x_mm(
    total_width_mm: float,
    ridge_x_mm: float,
    pitch_rad: float,
    spacing_mm: float,
    *,
    apex_clearance_mm: float = PURLIN_APEX_CLEARANCE_MM,
) -> list[float]:
    """Mirror purlin X positions for a double-sloped roof.

    Equal-length slopes share one slope-distance schedule mirrored about the
    ridge so each face lines up. The ridge-adjacent pair sits exactly
    ``apex_clearance_mm`` from the apex along each rafter.
    """
    if pitch_rad < 1e-9 or spacing_mm <= 0 or total_width_mm <= 0:
        return _roof_flat_x_mm(total_width_mm, spacing_mm)

    left_run = ridge_x_mm
    right_run = total_width_mm - ridge_x_mm
    cos_p = math.cos(pitch_rad)
    left_slope = left_run / cos_p if cos_p > 1e-9 else left_run
    right_slope = right_run / cos_p if cos_p > 1e-9 else right_run

    seat_kw = {
        "apex_clearance_mm": apex_clearance_mm,
        "pitch_rad": pitch_rad,
    }
    if abs(left_run - right_run) <= 1.0:
        distances = purlin_distances_along_slope_mm(
            left_slope, spacing_mm, **seat_kw
        )
        left_xs = [d * cos_p for d in distances]
        right_xs = [total_width_mm - d * cos_p for d in distances]
    else:
        left_dist = purlin_distances_along_slope_mm(
            left_slope, spacing_mm, **seat_kw
        )
        right_dist = purlin_distances_along_slope_mm(
            right_slope, spacing_mm, **seat_kw
        )
        left_xs = _slope_distances_to_x_mm(0.0, True, left_dist, pitch_rad)
        right_xs = _slope_distances_to_x_mm(
            total_width_mm, False, right_dist, pitch_rad
        )

    seen: set[float] = set()
    unique: list[float] = []
    for x in sorted(left_xs + right_xs):
        key = round(x, 6)
        if key in seen:
            continue
        seen.add(key)
        unique.append(x)
    return unique


def mono_pitch_purlin_x_mm(
    total_width_mm: float,
    pitch_rad: float,
    high_side: str,
    spacing_mm: float,
    *,
    apex_clearance_mm: float = PURLIN_APEX_CLEARANCE_MM,
) -> list[float]:
    """Purlin X positions for a mono-pitch roof (single slope)."""
    if pitch_rad < 1e-9 or spacing_mm <= 0 or total_width_mm <= 0:
        return _roof_flat_x_mm(total_width_mm, spacing_mm)

    cos_p = math.cos(pitch_rad)
    slope_len = total_width_mm / cos_p if cos_p > 1e-9 else total_width_mm
    distances = purlin_distances_along_slope_mm(
        slope_len,
        spacing_mm,
        apex_clearance_mm=apex_clearance_mm,
        pitch_rad=pitch_rad,
    )
    high_is_b = str(high_side).strip().upper() != "A"
    if high_is_b:
        return _slope_distances_to_x_mm(0.0, True, distances, pitch_rad)
    return _slope_distances_to_x_mm(total_width_mm, False, distances, pitch_rad)


def _roof_flat_x_mm(total_width_mm: float, spacing_mm: float) -> list[float]:
    """Even horizontal spacing for flat roofs (eave-to-eave)."""
    if spacing_mm <= 0 or total_width_mm <= 0:
        return [0.0, total_width_mm] if total_width_mm > 0 else []
    n = max(1, round(total_width_mm / spacing_mm))
    step = total_width_mm / n
    return [round(i * step, 3) for i in range(n + 1)]


def wall_girt_center_outside_x(
    x_column: float,
    total_width: float,
    *,
    col_outside_half_mm: float,
    girt_profile: str,
) -> float:
    """Side-wall girt centre with C-web back flush on the column outer flange face."""
    girt_seat = profile_girt_web_seat_mm(girt_profile)
    if x_column <= 1e-6:
        return x_column - col_outside_half_mm - girt_seat
    if x_column >= total_width - 1e-6:
        return x_column + col_outside_half_mm + girt_seat
    return x_column


def gable_girt_center_outside_z(
    z_column: float,
    total_length: float,
    *,
    col_outside_half_mm: float,
    girt_profile: str,
) -> float:
    """Gable-wall girt centre with C-web back flush on the column outer flange face."""
    girt_seat = profile_girt_web_seat_mm(girt_profile)
    if z_column <= 1e-6:
        return z_column - col_outside_half_mm - girt_seat
    if z_column >= total_length - 1e-6:
        return z_column + col_outside_half_mm + girt_seat
    return z_column


def profile_girt_web_seat_mm(girt_profile: str) -> float:
    """Centroid-to-web-back distance with h horizontal against the column face (mm)."""
    section = get_profile(girt_profile)
    return float(section["h"]) / 2.0


def wall_girt_roll_deg(x_column: float, total_width: float) -> float:
    """Roll nested Cee: h horizontal (outward), open side down."""
    if x_column <= 1e-6:
        return 90.0
    if x_column >= total_width - 1e-6:
        return 270.0
    return 90.0


def gable_girt_roll_deg(z_column: float, total_length: float) -> float:
    """Roll nested Cee on gable walls: h horizontal (outward), open side down."""
    if z_column <= 1e-6:
        return 270.0
    if z_column >= total_length - 1e-6:
        return 90.0
    return 90.0


def wall_girt_x_at_column_face(
    x_column: float,
    total_width: float,
    *,
    column_profile: str,
) -> float:
    """Girt centerline on outer column flange face."""
    half_b = profile_half_width_mm(column_profile)
    if x_column <= 1e-6:
        return x_column + half_b
    if x_column >= total_width - 1e-6:
        return x_column - half_b
    return x_column


def brace_node_at_column(
    x: float,
    y: float,
    z: float,
    *,
    column_profile: str,
    total_width: float,
    vertical: bool = True,
) -> tuple[float, float, float]:
    """Brace connection at column flange face (closed load path)."""
    if vertical:
        half_b = profile_half_width_mm(column_profile)
        if x <= 1e-6:
            return (x + half_b, y, z)
        if x >= total_width - 1e-6:
            return (x - half_b, y, z)
    return (x, y, z)


def _web_angle_deg(dx: float, dy: float) -> float:
    if dx < 1e-6:
        return 90.0
    return math.degrees(math.atan2(abs(dy), abs(dx)))


def _pratt_diagonal_angle_deg(
    panels: int,
    panel_index: int,
    span_x: float,
    *,
    y_bot0: float,
    y_bot1: float,
    y_top0: float,
    rise_mm: float,
) -> float:
    """Angle of diagonal web bottom[i] → top[i+1] (Pratt, non-mirrored)."""
    n = panels
    i = panel_index
    dx = abs(span_x) / n
    t_bot = i / n
    t_top = (i + 1) / n
    y_bottom = y_bot0 + (y_bot1 - y_bot0) * t_bot
    y_top = y_top0 + rise_mm * t_top
    return _web_angle_deg(dx, y_top - y_bottom)


def _optimal_pratt_panel_count(
    span_x: float,
    chord_depth_mm: float,
    rise_mm: float,
    *,
    y_bot0: float = 0.0,
    y_bot1: float = 0.0,
    y_top0: float = 0.0,
) -> int:
    """
    Choose panel count so Pratt diagonal webs stay within 30°–60° (target 45°).

    Evaluates each diagonal on the actual bottom/top chord lines (pitched or flat).
    """
    if span_x < 1e-6:
        return 2
    target_rad = math.radians(WEB_ANGLE_TARGET_DEG)
    ideal_dx = max(chord_depth_mm / math.tan(target_rad), 400.0)
    n = max(2, min(16, int(round(abs(span_x) / ideal_dx))))

    overall_pitch_deg = _web_angle_deg(abs(span_x), abs(rise_mm))

    def _all_diagonals_ok(count: int) -> bool:
        for i in range(count):
            angle = _pratt_diagonal_angle_deg(
                count,
                i,
                span_x,
                y_bot0=y_bot0,
                y_bot1=y_bot1,
                y_top0=y_top0,
                rise_mm=rise_mm,
            )
            # Shallow portal roofs: eave diagonals follow overall pitch (< 30°) per EC3 detailing.
            if (
                overall_pitch_deg < WEB_ANGLE_MIN_DEG
                and angle < WEB_ANGLE_MIN_DEG - 0.5
            ):
                continue
            if angle < WEB_ANGLE_MIN_DEG - 0.5 or angle > WEB_ANGLE_MAX_DEG + 0.5:
                return False
        return True

    for _ in range(24):
        if _all_diagonals_ok(n):
            return n
        shallow = _pratt_diagonal_angle_deg(
            n, 0, span_x, y_bot0=y_bot0, y_bot1=y_bot1, y_top0=y_top0, rise_mm=rise_mm
        )
        steep = _pratt_diagonal_angle_deg(
            n, n - 1, span_x, y_bot0=y_bot0, y_bot1=y_bot1, y_top0=y_top0, rise_mm=rise_mm
        )
        # Ridge panel: fewer panels → longer horizontal run → shallower diagonal.
        if steep > WEB_ANGLE_MAX_DEG + 0.5 and n > 2:
            n -= 1
        elif shallow < WEB_ANGLE_MIN_DEG and overall_pitch_deg >= WEB_ANGLE_MIN_DEG and n < 16:
            n += 1
        elif steep > WEB_ANGLE_MAX_DEG + 0.5 and n > 2:
            n -= 1
        elif n < 16:
            n += 1
        else:
            break
    return max(2, min(16, n))


def generate_standard_pratt_webs(
    start_node: tuple[float, float, float] | list[float],
    apex_node: tuple[float, float, float] | list[float],
    chord_depth: float,
    *,
    bottom_end_y: float | None = None,
    top_start_y: float | None = None,
    mirror_pratt: bool = False,
) -> PrattTrussLayout:
    """
    Subdivide a Pratt half-truss between start_node (eave / bottom chord start) and
    apex_node (ridge / top chord end).

    Interior web angles are constrained to 30°–60° (target 45° per EC3/IS 1225).
    chord_depth is the nominal clear depth between chords used for panel sizing (mm).
    """
    x0, y_bot0, z0 = (
        float(start_node[0]),
        float(start_node[1]),
        float(start_node[2]),
    )
    x1, y_top1, _z1 = float(apex_node[0]), float(apex_node[1]), float(apex_node[2])
    y_bot1 = float(bottom_end_y) if bottom_end_y is not None else y_bot0
    y_top0 = float(top_start_y) if top_start_y is not None else y_bot0
    span_x = x1 - x0
    rise = y_top1 - y_top0
    depth = max(float(chord_depth), 200.0)
    panels = _optimal_pratt_panel_count(
        abs(span_x),
        depth,
        abs(rise),
        y_bot0=y_bot0,
        y_bot1=y_bot1,
        y_top0=y_top0,
    )

    bottom: list[tuple[float, float, float]] = []
    top: list[tuple[float, float, float]] = []
    for i in range(panels + 1):
        t = i / panels
        x = x0 + span_x * t
        bottom.append((x, y_bot0 + (y_bot1 - y_bot0) * t, z0))
        top.append((x, y_top0 + (y_top1 - y_top0) * t, z0))

    webs: list[PrattWebMember] = []
    for i in range(panels):
        if mirror_pratt:
            if i % 2 == 0:
                web_start, web_end = bottom[i + 1], top[i + 1]
                kind: Literal["d", "v"] = "v"
            else:
                web_start, web_end = bottom[i], top[i + 1]
                kind = "d"
        else:
            if i % 2 == 0:
                web_start, web_end = bottom[i], top[i + 1]
                kind = "d"
            else:
                web_start, web_end = bottom[i + 1], top[i + 1]
                kind = "v"
        webs.append(PrattWebMember(start=web_start, end=web_end, kind=kind))

    return PrattTrussLayout(
        panels=panels,
        bottom_nodes=bottom,
        top_nodes=top,
        webs=webs,
    )


# --------------------------------------------------------------------------- #
# Full practical truss web-pattern registry
#
# Every truss is a 2D frame in the X–Y plane at one Z line. It has a top chord
# (follows the roof), a bottom chord (tie), and webs between shared panel nodes.
# Panel nodes are indexed 0..n left→right; top[i] sits directly above bottom[i],
# so a web is fully defined by (chord, node-index) endpoints. Connectivity is
# therefore guaranteed and degenerate (zero-length) members drop downstream.
# --------------------------------------------------------------------------- #

TrussType = Literal[
    "pratt",
    "howe",
    "warren",
    "fink",
    "king_post",
    "queen_post",
    "scissor",
]

# Diagonals/verticals carried (auto-panelled across each chord run).
PARAMETRIC_TRUSS_TYPES = frozenset({"pratt", "howe", "warren"})
# Fixed patterns that require a central apex (symmetric duo-pitch only).
APEX_TRUSS_TYPES = frozenset({"king_post", "queen_post", "fink", "scissor"})
ALL_TRUSS_TYPES = PARAMETRIC_TRUSS_TYPES | APEX_TRUSS_TYPES

# Panel count across the FULL span for fixed-pattern apex trusses.
_FIXED_TRUSS_PANELS: dict[str, int] = {
    "king_post": 2,
    "queen_post": 4,
    "fink": 4,
    "scissor": 4,
}

# Scissor: bottom chord lifts toward the centre by this fraction of the top rise.
SCISSOR_BOTTOM_RISE_FRACTION = 0.5

# A web end: which chord ("top" | "bottom") and which panel-node index.
WebEnd = tuple[str, int]
WebPair = tuple[WebEnd, WebEnd]


def truss_panel_count(span_x_mm: float, chord_depth_mm: float, rise_mm: float) -> int:
    """Panels across a chord run so diagonals sit in the 30°–60° band (EC3)."""
    return _optimal_pratt_panel_count(
        abs(span_x_mm), max(float(chord_depth_mm), 200.0), abs(rise_mm)
    )


def truss_fixed_panels(truss_type: str) -> int | None:
    """Full-span panel count for fixed-pattern trusses (None ⇒ auto-panel)."""
    return _FIXED_TRUSS_PANELS.get(truss_type)


def scissor_bottom_rise_mm(
    node_i: int, n: int, ridge_i: int, total_rise_mm: float
) -> float:
    """Vertical lift of a scissor bottom-chord node above the eave datum."""
    if ridge_i <= 0:
        return 0.0
    frac = min(node_i, n - node_i) / ridge_i
    return frac * SCISSOR_BOTTOM_RISE_FRACTION * float(total_rise_mm)


def mono_pitch_truss_web_plan(n: int, *, high_side: str = "B") -> list[WebPair]:
    """Webs for a mono-pitch portal truss (flat bottom chord, sloping top chord).

    Vertical at every panel node; each panel gets one diagonal rising toward the
    high end (Pratt toward the high side). Low eave end posts use full mono rise.
    """
    high_at_right = str(high_side).strip().upper() != "A"
    plan: list[WebPair] = []
    for i in range(n + 1):
        plan.append((("top", i), ("bottom", i)))
    if high_at_right:
        for i in range(n):
            plan.append((("bottom", i), ("top", i + 1)))
    else:
        for i in range(n):
            plan.append((("bottom", i + 1), ("top", i)))
    return plan


def truss_web_plan(truss_type: str, n: int, ridge_i: int | None) -> list[WebPair]:
    """
    Web members for an n-panel truss as (chord, node-index) endpoint pairs.

    ridge_i is the apex node index for pitched trusses (None ⇒ parallel chords).
    Verticals are emitted at every node; zero-depth ones at the eaves drop later,
    which also yields the correct end post on mono / parallel trusses.
    """
    m = ridge_i if ridge_i is not None else n

    def v(i: int) -> WebPair:
        return (("top", i), ("bottom", i))

    def d(a: str, ai: int, b: str, bi: int) -> WebPair:
        return ((a, ai), (b, bi))

    plan: list[WebPair] = []

    if truss_type == "warren":
        # Zig-zag of equal triangles, no verticals.
        for i in range(n):
            if i % 2 == 0:
                plan.append(d("bottom", i, "top", i + 1))
            else:
                plan.append(d("top", i, "bottom", i + 1))
        return plan

    if truss_type == "howe":
        # Verticals + diagonals sloping down toward the eaves (Pratt mirror).
        for i in range(n + 1):
            plan.append(v(i))
        for i in range(0, m):
            plan.append(d("top", i, "bottom", i + 1))
        for i in range(m, n):
            plan.append(d("top", i + 1, "bottom", i))
        return plan

    if truss_type == "king_post":
        # n == 2: single central post under the apex.
        plan.append(v(m))
        return plan

    if truss_type == "queen_post":
        # n == 4: two posts + struts up to the apex.
        plan.append(v(1))
        plan.append(v(3))
        plan.append(d("bottom", 1, "top", 2))
        plan.append(d("bottom", 3, "top", 2))
        return plan

    if truss_type == "fink":
        # n == 4: central post + struts up to the mid-rafters (classic "W").
        plan.append(v(2))
        plan.append(d("bottom", 2, "top", 1))
        plan.append(d("bottom", 2, "top", 3))
        return plan

    if truss_type == "scissor":
        # n == 4: crossing diagonals over a raised bottom chord + central post.
        plan.append(v(2))
        plan.append(d("bottom", 1, "top", 3))
        plan.append(d("bottom", 3, "top", 1))
        return plan

    # default: pratt — verticals + diagonals rising toward the apex/centre.
    for i in range(n + 1):
        plan.append(v(i))
    for i in range(0, m):
        plan.append(d("bottom", i, "top", i + 1))
    for i in range(m, n):
        plan.append(d("bottom", i + 1, "top", i))
    return plan


def sag_rod_bay_fractions(bay_spacing_mm: float) -> list[float]:
    """
    Normalized Z positions along a bay for anti-sag rows (0–1).

    - bay <= 5500 mm: one row at mid-span (0.5).
    - bay > 5500 mm: two rows at 1/3 and 2/3 (LTB / IS 1225 practice).
    """
    spacing = float(bay_spacing_mm)
    if spacing <= SAG_BAY_SINGLE_ROW_MAX_MM:
        return [0.5]
    return [1.0 / 3.0, 2.0 / 3.0]


def sag_rod_z_positions(z0: float, z1: float, bay_spacing_mm: float) -> list[float]:
    """Absolute Z coordinates for sag-rod rows in a portal bay."""
    span = z1 - z0
    return [z0 + fraction * span for fraction in sag_rod_bay_fractions(bay_spacing_mm)]


def bracing_requires_tie_beams() -> bool:
    """X-bracing bays require longitudinal ties for a closed load path."""
    return True


def tie_beams_for_braced_bays(
    x_positions: list[float],
    frame_zs: list[float],
    *,
    total_width: float,
    eave_y: float,
    ridge_y_at_x,
    braced_bay_indices: list[int],
) -> list[TieBeamSpec]:
    """
    Longitudinal tie beams at column–rafter nodes for braced portal bays.

    ridge_y_at_x: callable(x) -> ridge/eave elevation at column line.
    """
    specs: list[TieBeamSpec] = []
    if len(frame_zs) < 2:
        return specs
    for bay_i in braced_bay_indices:
        if bay_i < 0 or bay_i >= len(frame_zs) - 1:
            continue
        z0, z1 = frame_zs[bay_i], frame_zs[bay_i + 1]
        for x in x_positions:
            ridge_y = float(ridge_y_at_x(x))
            specs.append(
                TieBeamSpec(x=x, y=eave_y, z0=z0, z1=z1, level="eave"),
            )
            if abs(ridge_y - eave_y) > 50.0:
                specs.append(
                    TieBeamSpec(x=x, y=ridge_y, z0=z0, z1=z1, level="ridge"),
                )
    return specs


def resolve_generate_tie_beams(
    generate_tie_beams: bool,
    use_bracing: bool,
) -> bool:
    """Enforce ties when bracing is on (dependency rule)."""
    if use_bracing and bracing_requires_tie_beams():
        return True
    return generate_tie_beams


def end_wall_braced_bay_indices(frame_count: int) -> list[int]:
    """First and last Z bays — standard end-wall bracing zones."""
    if frame_count < 2:
        return []
    return [0, frame_count - 2]

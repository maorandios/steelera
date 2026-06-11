"""Infer full X-brace geometry from one sketched diagonal leg."""

from __future__ import annotations

import math
import re

from schemas.elements import ProjectElementMm

TOL_MM = 150.0
FRAME_Z_TOL_MM = 200.0
PANEL_X_TOL_MM = 350.0
LOW_EAVE_Y_MM = 2000.0

_TRUSS_TC_RE = re.compile(r"-truss-tc-(\d+)-", re.I)
_TRUSS_BC_RE = re.compile(r"-truss-bc-(\d+)-", re.I)


def _dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _span_key(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Order-independent span id (must match model_edit._span_key)."""
    return tuple(sorted((start, end)))

def _is_column(element: ProjectElementMm) -> bool:
    et = (element.element_type or "").lower()
    if et == "column":
        return True
    return "-col-" in element.id.lower()


def _point_to_segment_dist(
    pt: tuple[float, float, float],
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    ax, ay, az = a
    bx, by, bz = b
    px, py, pz = pt
    dx, dy, dz = bx - ax, by - ay, bz - az
    len_sq = dx * dx + dy * dy + dz * dz
    if len_sq < 1.0:
        return _dist(pt, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy + (pz - az) * dz) / len_sq))
    proj = (ax + t * dx, ay + t * dy, az + t * dz)
    return _dist(pt, proj)


def _nearest_column(
    pt: tuple[float, float, float],
    elements: list[ProjectElementMm],
    *,
    max_dist_mm: float = 1500.0,
) -> ProjectElementMm | None:
    best: ProjectElementMm | None = None
    best_d = float("inf")
    for el in elements:
        if not _is_column(el):
            continue
        ep = _member_endpoints(el)
        if not ep:
            continue
        d = _point_to_segment_dist(pt, ep[0], ep[1])
        if d < best_d:
            best_d = d
            best = el
    if best is None or best_d > max_dist_mm:
        return None
    return best


def _column_bottom_top(
    element: ProjectElementMm,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    ep = _member_endpoints(element)
    if not ep:
        return None
    low, high = ep
    if low[1] <= high[1]:
        return low, high
    return high, low


def _diagonal_match_score(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    p: tuple[float, float, float],
    q: tuple[float, float, float],
) -> float:
    return min(
        _dist(start_mm, p) + _dist(end_mm, q),
        _dist(start_mm, q) + _dist(end_mm, p),
    )


def _member_endpoints(
    element: ProjectElementMm,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    nodes = element.nodes or {}
    start = nodes.get("start") or nodes.get("bottom")
    end = nodes.get("end") or nodes.get("top")
    if start and end and len(start) >= 3 and len(end) >= 3:
        return (
            (float(start[0]), float(start[1]), float(start[2])),
            (float(end[0]), float(end[1]), float(end[2])),
        )

    pos = element.position_mm
    size = element.size_mm
    axis = (element.axis or "y").lower()
    half = float(size.get(axis, element.length_mm)) / 2.0
    cx, cy, cz = float(pos["x"]), float(pos["y"]), float(pos["z"])
    if axis == "x":
        return (cx - half, cy, cz), (cx + half, cy, cz)
    if axis == "z":
        return (cx, cy, cz - half), (cx, cy, cz + half)
    return (cx, cy - half, cz), (cx, cy + half, cz)


def _collect_endpoints(
    elements: list[ProjectElementMm],
    *,
    truss_only: bool = False,
    min_y: float | None = None,
) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for el in elements:
        if truss_only and not _is_truss_chord(el):
            continue
        ep = _member_endpoints(el)
        if not ep:
            continue
        for pt in ep:
            if min_y is not None and pt[1] < min_y:
                continue
            out.append(pt)
    return out


def _collect_truss_segments(
    elements: list[ProjectElementMm],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    segs: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for el in elements:
        if not _is_truss_chord(el):
            continue
        ep = _member_endpoints(el)
        if ep:
            segs.append(ep)
    return segs


def _point_on_frame_at_x(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    frame_z: float,
    x_mm: float,
    *,
    reference_y: float | None = None,
) -> tuple[float, float, float] | None:
    """Elevation on a truss frame line at a given X (interpolate along TC segments)."""
    best: tuple[float, float, float] | None = None
    best_score = float("inf")

    for s, e in segments:
        if abs(s[2] - frame_z) > FRAME_Z_TOL_MM and abs(e[2] - frame_z) > FRAME_Z_TOL_MM:
            continue

        for pt in (s, e):
            if abs(pt[2] - frame_z) > FRAME_Z_TOL_MM:
                continue
            dx = abs(pt[0] - x_mm)
            if dx > PANEL_X_TOL_MM:
                continue
            score = dx + (abs(pt[1] - reference_y) * 0.01 if reference_y is not None else 0)
            if score < best_score:
                best_score = score
                best = pt

        if abs(s[2] - frame_z) > FRAME_Z_TOL_MM or abs(e[2] - frame_z) > FRAME_Z_TOL_MM:
            continue
        x0, x1 = s[0], e[0]
        lo, hi = min(x0, x1), max(x0, x1)
        if x_mm < lo - PANEL_X_TOL_MM or x_mm > hi + PANEL_X_TOL_MM:
            continue
        if abs(x1 - x0) < 1.0:
            t = 0.5
        else:
            t = max(0.0, min(1.0, (x_mm - x0) / (x1 - x0)))
        interp = (
            s[0] + t * (e[0] - s[0]),
            s[1] + t * (e[1] - s[1]),
            s[2] + t * (e[2] - s[2]),
        )
        if abs(interp[2] - frame_z) > FRAME_Z_TOL_MM:
            continue
        dx = abs(interp[0] - x_mm)
        score = dx + (abs(interp[1] - reference_y) * 0.01 if reference_y is not None else 0)
        if score < best_score:
            best_score = score
            best = interp

    return best


def _infer_roof_x_corners(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    elements: list[ProjectElementMm],
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
] | None:
    """X-brace between adjacent frames using truss top-chord panel nodes."""
    sx, sy, sz = start_mm
    ex, ey, ez = end_mm
    if abs(ez - sz) < 200:
        return None

    z_lo, z_hi = (sz, ez) if sz < ez else (ez, sz)
    p_start = start_mm if abs(sz - z_lo) < 1 else end_mm
    p_end = end_mm if abs(ez - z_hi) < 1 else start_mm
    x_a, y_a, z_a = p_start
    x_b, y_b, z_b = p_end

    segments = _collect_truss_segments(elements)
    if not segments:
        return None

    comp_on_lo = _point_on_frame_at_x(segments, z_lo, x_b, reference_y=y_b)
    comp_on_hi = _point_on_frame_at_x(segments, z_hi, x_a, reference_y=y_a)
    if comp_on_lo is None or comp_on_hi is None:
        return None

    return p_start, p_end, comp_on_lo, comp_on_hi


def _infer_wall_x_corners_from_coords(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
] | None:
    """Fallback when column hosts are unavailable."""
    sx, sy, sz = start_mm
    ex, ey, ez = end_mm
    dz = abs(ez - sz)
    dx = abs(ex - sx)

    if dz >= dx and dz > 200:
        c1, c4 = (sx, sy, sz), (sx, sy, ez)
        c2, c3 = (ex, ey, sz), (ex, ey, ez)
    elif dx > dz and dx > 200:
        c1, c2 = (sx, sy, sz), (ex, sy, sz)
        c4, c3 = (sx, ey, ez), (ex, ey, ez)
    else:
        return None

    diag1 = (c1, c3)
    diag2 = (c2, c4)
    if _diagonal_match_score(start_mm, end_mm, *diag1) <= _diagonal_match_score(
        start_mm, end_mm, *diag2
    ):
        return diag1[0], diag1[1], diag2[0], diag2[1]
    return diag2[0], diag2[1], diag1[0], diag1[1]


def _column_by_id(
    elements: list[ProjectElementMm],
    element_id: str | None,
) -> ProjectElementMm | None:
    if not element_id:
        return None
    for el in elements:
        if el.id == element_id and _is_column(el):
            return el
    return None


def _infer_wall_x_corners(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    elements: list[ProjectElementMm],
    *,
    start_element_id: str | None = None,
    end_element_id: str | None = None,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
] | None:
    """Full X-brace between two columns: both corner-to-corner diagonals."""
    col_a = _column_by_id(elements, start_element_id)
    col_b = _column_by_id(elements, end_element_id)
    if col_a is None:
        col_a = _nearest_column(start_mm, elements)
    if col_b is None:
        col_b = _nearest_column(end_mm, elements)
    if col_a is None or col_b is None or col_a.id == col_b.id:
        return _infer_wall_x_corners_from_coords(start_mm, end_mm)

    a_ends = _column_bottom_top(col_a)
    b_ends = _column_bottom_top(col_b)
    if not a_ends or not b_ends:
        return _infer_wall_x_corners_from_coords(start_mm, end_mm)

    a_bot, a_top = a_ends
    b_bot, b_top = b_ends

    diag1 = (a_bot, b_top)
    diag2 = (a_top, b_bot)
    if _diagonal_match_score(start_mm, end_mm, *diag1) <= _diagonal_match_score(
        start_mm, end_mm, *diag2
    ):
        return diag1[0], diag1[1], diag2[0], diag2[1]
    return diag2[0], diag2[1], diag1[0], diag1[1]


def _is_truss_chord(element: ProjectElementMm) -> bool:
    et = (element.element_type or "").lower()
    eid = element.id.lower()
    if et in ("truss_chord", "truss_web"):
        return True
    return "-truss-tc-" in eid or "-truss-bc-" in eid


def _near_truss_chord(
    pt: tuple[float, float, float],
    elements: list[ProjectElementMm],
    *,
    tol_mm: float = PANEL_X_TOL_MM,
) -> bool:
    for el in elements:
        if not _is_truss_chord(el):
            continue
        ep = _member_endpoints(el)
        if not ep:
            continue
        for corner in ep:
            if _dist(pt, corner) <= tol_mm:
                return True
    return False


def infer_x_brace_corners(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    elements: list[ProjectElementMm] | None = None,
    *,
    start_element_id: str | None = None,
    end_element_id: str | None = None,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
] | None:
    """Return (a, b, c, d) for place_bracing_cross: leg1 a→b, leg2 c→d."""
    els = elements or []
    dz = abs(end_mm[2] - start_mm[2])
    dx = abs(end_mm[0] - start_mm[0])
    on_truss = bool(els) and (
        _near_truss_chord(start_mm, els) or _near_truss_chord(end_mm, els)
    )

    wall = _infer_wall_x_corners(
        start_mm,
        end_mm,
        els,
        start_element_id=start_element_id,
        end_element_id=end_element_id,
    )
    if wall and not on_truss:
        return wall

    if on_truss and max(start_mm[1], end_mm[1]) > LOW_EAVE_Y_MM + 500 and dz >= dx:
        roof = _infer_roof_x_corners(start_mm, end_mm, els)
        if roof:
            return roof

    return wall


def estimate_roof_panel_count(
    slope_length_mm: float,
    *,
    width_mm: float = 12000.0,
    height_mm: float = 6000.0,
) -> int:
    """Screening panel count for long truss slopes."""
    target_panel_mm = 4000.0
    return max(1, min(6, round(slope_length_mm / target_panel_mm)))

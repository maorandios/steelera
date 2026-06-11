"""Infer full X-brace geometry from one sketched diagonal leg."""

from __future__ import annotations

import math

from schemas.elements import ProjectElementMm

TOL_MM = 150.0


def _dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])


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
) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for el in elements:
        ep = _member_endpoints(el)
        if ep:
            out.append(ep[0])
            out.append(ep[1])
    return out


def _nearest_point(
    target: tuple[float, float, float],
    candidates: list[tuple[float, float, float]],
    max_dist: float = TOL_MM * 4,
) -> tuple[float, float, float] | None:
    best: tuple[float, float, float] | None = None
    best_d = max_dist
    for c in candidates:
        d = _dist(target, c)
        if d < best_d:
            best_d = d
            best = c
    return best


def _lerp_y(
    x: float,
    z: float,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
) -> float:
    dx = p1[0] - p0[0]
    dz = p1[2] - p0[2]
    span = math.hypot(dx, dz)
    if span < 1.0:
        return p0[1]
    tx = (x - p0[0]) / dx if abs(dx) > 1.0 else 0.5
    tz = (z - p0[2]) / dz if abs(dz) > 1.0 else 0.5
    t = max(0.0, min(1.0, (tx + tz) / 2.0 if abs(dx) > 1 and abs(dz) > 1 else tx or tz))
    return p0[1] + t * (p1[1] - p0[1])


def infer_x_brace_corners(
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    elements: list[ProjectElementMm] | None = None,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
] | None:
    """Return (a, b, c, d) for place_bracing_cross: leg1 a→b, leg2 c→d."""
    sx, sy, sz = start_mm
    ex, ey, ez = end_mm
    endpoints = _collect_endpoints(elements or [])

    dz = abs(ez - sz)
    dx = abs(ex - sx)

    if dz >= dx and dz > 200:
        # Bay between adjacent frames (Z).
        c1 = (sx, sy, sz)
        c2 = (ex, ey, sz)
        c3 = (ex, ey, ez)
        c4 = (sx, sy, ez)
    elif dx > dz and dx > 200:
        # Bay along X (panel on one frame).
        c1 = (sx, sy, sz)
        c2 = (ex, sy, sz)
        c3 = (ex, ey, ez)
        c4 = (sx, ey, ez)
    else:
        return None

    leg1_start = start_mm
    leg1_end = end_mm
    d12 = _dist(c1, c2) + _dist(c3, c4)
    d14 = _dist(c1, c4) + _dist(c2, c3)

    if _dist(leg1_start, c1) + _dist(leg1_end, c4) < _dist(leg1_start, c2) + _dist(leg1_end, c3):
        leg2_start, leg2_end = c2, c3
    else:
        leg2_start, leg2_end = c4, c2

    if elements:
        ns = _nearest_point(leg2_start, endpoints)
        ne = _nearest_point(leg2_end, endpoints)
        if ns:
            leg2_start = ns
        if ne:
            leg2_end = ne
        ns = _nearest_point(leg1_start, endpoints)
        ne = _nearest_point(leg1_end, endpoints)
        if ns:
            leg1_start = ns
        if ne:
            leg1_end = ne

    return leg1_start, leg1_end, leg2_start, leg2_end


def estimate_roof_panel_count(
    slope_length_mm: float,
    *,
    width_mm: float = 12000.0,
    height_mm: float = 6000.0,
) -> int:
    """Screening panel count for long truss slopes."""
    # Practical cap: ~4 m panels along the slope (not full truss auto-panel count).
    target_panel_mm = 4000.0
    return max(1, min(6, round(slope_length_mm / target_panel_mm)))

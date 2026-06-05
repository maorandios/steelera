"""
Element-agnostic structural validator.

Guarantees the AI's layout is physically sound before rendering. It does NOT know
about sheds; it only checks generic invariants: finite geometry, real lengths, and
that the PRIMARY load path (columns/rafters/chords/ties) is actually connected —
no member endpoint floating in mid-air. Returns actionable errors for AI self-correction.
"""

from __future__ import annotations

import math
from typing import Any

Vec = tuple[float, float, float]

_PRIMARY = {"column", "rafter", "truss_chord", "tie_beam"}
_TOL_MM = 50.0
_MIN_LENGTH_MM = 1.0


def _v(p: list[float]) -> Vec:
    return (float(p[0]), float(p[1]), float(p[2]))


def _finite(p: Vec) -> bool:
    return all(math.isfinite(c) for c in p)


def _dist(a: Vec, b: Vec) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _point_supported_by_segment(p: Vec, a: Vec, b: Vec) -> bool:
    """True if p lies on (or at an end of) segment a→b within tolerance."""
    abv = tuple(b[i] - a[i] for i in range(3))
    ab2 = sum(c * c for c in abv)
    if ab2 < 1e-9:
        return _dist(p, a) < _TOL_MM
    t = sum((p[i] - a[i]) * abv[i] for i in range(3)) / ab2
    t = max(0.0, min(1.0, t))
    closest = tuple(a[i] + t * abv[i] for i in range(3))
    return _dist(p, closest) < _TOL_MM


def validate_macro_members(macro_members: list[dict[str, Any]]) -> list[str]:
    """Return a list of human-readable structural errors (empty = sound)."""
    errors: list[str] = []
    if not macro_members:
        return ["The layout produced zero members. Add operations that place steel."]

    primaries: list[tuple[str, Vec, Vec]] = []
    for m in macro_members:
        nodes = m.get("nodes") or {}
        start = nodes.get("start")
        end = nodes.get("end")
        if not start or not end:
            errors.append(f"Member '{m.get('id')}' is missing resolved start/end nodes.")
            continue
        s, e = _v(start), _v(end)
        if not (_finite(s) and _finite(e)):
            errors.append(f"Member '{m.get('id')}' has non-finite coordinates.")
            continue
        if _dist(s, e) < _MIN_LENGTH_MM:
            errors.append(
                f"Member '{m.get('id')}' has near-zero length; its start and end "
                f"grid references resolve to the same point."
            )
        if m.get("element_type") in _PRIMARY:
            primaries.append((str(m.get("id")), s, e))

    # Connectivity of the primary load path: every endpoint must rest on the ground
    # or connect to another primary member (endpoint or along its length).
    for pid, s, e in primaries:
        for label, pt in (("start", s), ("end", e)):
            if abs(pt[1]) < _TOL_MM:  # on the ground plane
                continue
            supported = any(
                oid != pid and _point_supported_by_segment(pt, os, oe)
                for oid, os, oe in primaries
            )
            if not supported:
                errors.append(
                    f"Member '{pid}' {label} endpoint at "
                    f"(x={pt[0]:.0f}, y={pt[1]:.0f}, z={pt[2]:.0f}) mm is unsupported: "
                    f"it does not meet the ground or any other primary member. "
                    f"Add a supporting column/member there or align the endpoint to an "
                    f"existing node (check column top vs roof elevation)."
                )

    # Out-of-plane stability: transverse frames sit at distinct Z planes. If there are
    # 2+ such planes but NO member spans between them, the frames are disconnected in
    # the length direction (laterally unstable) — the classic "missing longitudinal steel".
    z_planes: set[float] = set()
    spans_z = False
    for m in macro_members:
        nodes = m.get("nodes") or {}
        start, end = nodes.get("start"), nodes.get("end")
        if not start or not end:
            continue
        sz, ez = round(float(start[2]), 1), round(float(end[2]), 1)
        z_planes.add(sz)
        z_planes.add(ez)
        if abs(sz - ez) > _TOL_MM:
            spans_z = True
    if len(z_planes) >= 2 and not spans_z:
        errors.append(
            "The frames sit at multiple positions along the length (Z) but nothing "
            "connects them — the structure is unstable lengthwise. Add longitudinal "
            "members spanning between Z frames: eave (and ridge/apex) tie beams via "
            "array_adjacent axis='z', roof purlins, and any requested sag rods/bracing."
        )

    # De-duplicate while preserving order; cap so the AI gets a focused list.
    seen: set[str] = set()
    unique = [e for e in errors if not (e in seen or seen.add(e))]
    return unique[:12]

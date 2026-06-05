"""Normalize AI grid references to engine-canonical names."""

from __future__ import annotations

import re

from schemas.spatial_grid import GridNodeReference, StructuralGridLayout, StructuralMember

_ELEVATION_ALIASES: dict[str, str] = {
    "rooftop": "roof",
    "roof_top": "roof",
    "roof_level": "roof",
    "top": "roof",
    "ridge_line": "ridge",
    "ridge_level": "ridge",
    "peak": "apex",
    "apex_level": "apex",
    "summit": "apex",
    "base": "ground",
    "floor": "ground",
    "grade": "ground",
    "foundation": "ground",
    "portal": "eave",
    "eave_level": "eave",
    "haunch": "eave",
    "column_top": "eave",
}


def normalize_axis_ref(axis: str, *, is_x: bool = True) -> str:
    """
    Canonicalize axis labels: B-1/3 → B+1/3, strip spaces, uppercase X letters.
    """
    text = str(axis).strip()
    if not text:
        raise ValueError("axis reference is empty")

    if is_x:
        cleaned = text.upper().replace(" ", "")
        m = re.match(r"^([A-Z]+)(?:[-+](\d+/\d+))?$", cleaned)
        if not m:
            return cleaned
        if m.group(2):
            return f"{m.group(1)}+{m.group(2)}"
        return m.group(1)

    cleaned = text.replace(" ", "")
    m = re.match(r"^(\d+)(?:[-+](\d+/\d+))?$", cleaned)
    if not m:
        return cleaned
    if m.group(2):
        return f"{m.group(1)}+{m.group(2)}"
    return m.group(1)


def normalize_elevation(elevation: str) -> str:
    """Map common AI labels to ground | eave | roof | apex | ridge (+ optional /n fraction)."""
    text = str(elevation).strip().lower().replace(" ", "_").replace("-", "_")
    if not text:
        return "ground"

    if "+" in text:
        base, frac = text.split("+", 1)
        base_norm = normalize_elevation(base)
        if re.fullmatch(r"\d+/\d+", frac.strip()):
            return f"{base_norm}+{frac.strip()}"
        return normalize_elevation(f"{base_norm}_{frac}")

    return _ELEVATION_ALIASES.get(text, text)


def normalize_node_ref(ref: GridNodeReference) -> GridNodeReference:
    x = normalize_axis_ref(ref.x_axis, is_x=True)
    z = normalize_axis_ref(ref.z_axis, is_x=False)
    elev = normalize_elevation(ref.elevation)
    return ref.model_copy(update={"x_axis": x, "z_axis": z, "elevation": elev})


def normalize_member(member: StructuralMember) -> StructuralMember:
    return member.model_copy(
        update={
            "start_node": normalize_node_ref(member.start_node),
            "end_node": normalize_node_ref(member.end_node),
        }
    )


def normalize_layout(layout: StructuralGridLayout) -> StructuralGridLayout:
    members = [normalize_member(m) for m in layout.structural_members]
    return layout.model_copy(update={"structural_members": members})

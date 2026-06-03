"""
Anchor resolution via explicit member connection nodes.

Snaps the new member's origin node (bottom for columns, start for beams)
to the anchor coordinate. Members always grow in the +length direction.
"""

from core.member_nodes import ensure_member_nodes, position_mm_from_node
from schemas.elements import AddStructuralElementInput, ProjectElementMm


def _find_element(
    element_id: str, existing: list[ProjectElementMm]
) -> ProjectElementMm:
    key = element_id.strip().lower()
    for el in existing:
        if el.id.lower() == key:
            return el
    ids = ", ".join(e.id for e in existing) or "(none)"
    raise ValueError(f"anchor_element_id '{element_id}' not found. Existing ids: {ids}")


def _anchor_xyz_for_column_on_beam(
    anchor_el: ProjectElementMm,
    anchor_point: str,
) -> list[float]:
    """Get the top-face attachment point on a horizontal beam for a vertical column."""
    nodes = ensure_member_nodes(anchor_el)
    rise = float(anchor_el.size_mm["y"])
    length = float(anchor_el.length_mm)
    start = nodes.get("start", [0, 0, 0])

    if anchor_point == "CENTER":
        if "top_center" in nodes:
            return list(nodes["top_center"])
        return [start[0] + length * 0.5, start[1] + rise, start[2]]

    if anchor_point == "END":
        if "top_end" in nodes:
            return list(nodes["top_end"])
        end = nodes.get("end", start)
        return [end[0], end[1] + rise, end[2]]

    if anchor_point in ("START", "TOP"):
        if anchor_point == "TOP" and "top" in nodes:
            return list(nodes["top"])
        if "top" in nodes and anchor_point == "START":
            return list(nodes["top"])
        return [start[0], start[1] + rise, start[2]]

    if anchor_point == "BOTTOM":
        return list(nodes.get("bottom", start))

    raise ValueError(f"Unsupported anchor_point '{anchor_point}' for column-on-beam")


def resolve_position_from_anchor(
    payload: AddStructuralElementInput,
    existing_elements: list[ProjectElementMm],
    *,
    new_axis: str,
    new_length_mm: float,
) -> dict[str, float]:
    if not payload.uses_anchor():
        raise ValueError("resolve_position_from_anchor called without anchor")

    anchor_el = _find_element(payload.anchor_element_id, existing_elements)
    anchor_point = payload.anchor_point

    # Column on horizontal beam: bottom of column on top face, column grows +Y.
    if new_axis == "y" and anchor_el.axis in ("x", "z"):
        anchor_xyz = _anchor_xyz_for_column_on_beam(anchor_el, anchor_point)
        return position_mm_from_node("bottom", anchor_xyz, "y", new_length_mm)

    nodes = ensure_member_nodes(anchor_el)
    node_map = {
        "TOP": "top",
        "BOTTOM": "bottom",
        "START": "start",
        "END": "end",
        "CENTER": "center",
    }
    node_key = node_map.get(anchor_point)
    if not node_key or node_key not in nodes:
        available = ", ".join(sorted(nodes.keys())) or "(none)"
        raise ValueError(
            f"anchor_point '{anchor_point}' unavailable on '{anchor_el.id}'. "
            f"Nodes: {available}"
        )

    anchor_xyz = list(nodes[node_key])
    attach_node = "bottom" if new_axis == "y" else "start"
    return position_mm_from_node(attach_node, anchor_xyz, new_axis, new_length_mm)

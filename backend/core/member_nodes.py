"""Connection node math for structural members (backend Y-up coords)."""

from schemas.elements import ProjectElementMm


def _vertical_extent_mm(element: ProjectElementMm) -> float:
    """World-Y height of the member cross-section bounding box (mm)."""
    return float(element.size_mm["y"])


def compute_member_nodes(element: ProjectElementMm) -> dict[str, list[float]]:
    """
    Connection nodes at key attachment points.

    Vertical column (axis y): bottom / top along +Y.
    Horizontal beam (axis x/z): start / end along length, plus top face nodes
    in world +Y for column-on-beam anchoring.
    """
    axis = element.axis
    pos = element.position_mm
    length_mm = float(element.length_mm)
    x = float(pos["x"])
    y = float(pos["y"])
    z = float(pos["z"])
    rise = _vertical_extent_mm(element)

    if axis == "y":
        mid_y = y + length_mm * 0.5
        return {
            "bottom": [x, y, z],
            "top": [x, y + length_mm, z],
            "center": [x, mid_y, z],
        }
    if axis == "x":
        mid_x = x + length_mm * 0.5
        return {
            "start": [x, y, z],
            "end": [x + length_mm, y, z],
            "center": [mid_x, y, z],
            "bottom": [x, y, z],
            "top": [x, y + rise, z],
            "top_center": [mid_x, y + rise, z],
            "top_end": [x + length_mm, y + rise, z],
        }
    if axis == "z":
        mid_z = z + length_mm * 0.5
        return {
            "start": [x, y, z],
            "end": [x, y, z + length_mm],
            "center": [x, y, mid_z],
            "bottom": [x, y, z],
            "top": [x, y + rise, z],
            "top_center": [x, y + rise, mid_z],
            "top_end": [x, y + rise, z + length_mm],
        }
    raise ValueError(f"Invalid axis: {axis}")


def ensure_member_nodes(element: ProjectElementMm) -> dict[str, list[float]]:
    """Return stored nodes merged with computed attachment nodes."""
    computed = compute_member_nodes(element)
    if not element.nodes:
        return computed

    stored = dict(element.nodes)
    if element.axis in ("x", "z"):
        for key in ("bottom", "top", "top_center", "top_end", "center", "start", "end"):
            if key in computed:
                stored[key] = computed[key]
    elif element.axis == "y":
        for key in ("bottom", "top", "center"):
            if key in computed:
                stored[key] = computed[key]
    return stored


def position_mm_from_node(
    attach_node: str,
    node_xyz: list[float],
    axis: str,
    length_mm: float,
) -> dict[str, float]:
    """Derive position_mm so that attach_node sits exactly at node_xyz."""
    nx, ny, nz = (float(node_xyz[0]), float(node_xyz[1]), float(node_xyz[2]))

    if axis == "y":
        if attach_node == "bottom":
            return {"x": nx, "y": ny, "z": nz}
        if attach_node == "top":
            return {"x": nx, "y": ny - length_mm, "z": nz}
        raise ValueError(f"Invalid attach node '{attach_node}' for axis y")

    if axis == "x":
        if attach_node == "start":
            return {"x": nx, "y": ny, "z": nz}
        if attach_node == "end":
            return {"x": nx - length_mm, "y": ny, "z": nz}
        raise ValueError(f"Invalid attach node '{attach_node}' for axis x")

    if axis == "z":
        if attach_node == "start":
            return {"x": nx, "y": ny, "z": nz}
        if attach_node == "end":
            return {"x": nx, "y": ny, "z": nz - length_mm}
        raise ValueError(f"Invalid attach node '{attach_node}' for axis z")

    raise ValueError(f"Invalid axis: {axis}")

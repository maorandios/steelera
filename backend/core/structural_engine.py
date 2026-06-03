"""
Universal parametric engine: map steel section specs to 3D bounding boxes.

Section cross-section uses width (Y) and height (Z) in local space.
Member length extends along the specified world axis (x, y, or z).
Position is the min-corner of the axis-aligned bounding box.
"""

from schemas.project import ProjectState
from schemas.structural import (
    RenderedStructuralElement,
    StructuralElementSpec,
)

SHAPE_COLORS = {
    "I-beam": "#94a3b8",
    "C-channel": "#64748b",
    "Box": "#71717a",
    "Pipe": "#a1a1aa",
}


def _section_bbox(spec: StructuralElementSpec) -> tuple[float, float, float]:
    """Local size (length_along_axis, section_width, section_depth) before axis swap."""
    mappers = {
        "I-beam": _bbox_for_i_beam,
        "C-channel": _bbox_for_c_channel,
        "Box": _bbox_for_box,
        "Pipe": _bbox_for_pipe,
    }
    mapper = mappers[spec.shape_type]
    local = mapper(spec)
    return (spec.length, local[1], local[2])


def _bbox_for_i_beam(spec: StructuralElementSpec) -> tuple[float, float, float]:
    flange_overhang = max(spec.width * 0.15, spec.thickness)
    overall_width = spec.width + 2 * flange_overhang
    return (spec.length, overall_width, spec.height)


def _bbox_for_c_channel(spec: StructuralElementSpec) -> tuple[float, float, float]:
    lip = max(spec.thickness * 1.5, spec.height * 0.08)
    overall_width = spec.width + lip
    return (spec.length, overall_width, spec.height)


def _bbox_for_box(spec: StructuralElementSpec) -> tuple[float, float, float]:
    return (spec.length, spec.width, spec.height)


def _bbox_for_pipe(spec: StructuralElementSpec) -> tuple[float, float, float]:
    diameter = max(spec.width, spec.height)
    return (spec.length, diameter, diameter)


def _orient_size(
    length: float, sy: float, sz: float, axis: str
) -> tuple[float, float, float]:
    """Map local (length, section_y, section_z) to world (x, y, z) extents."""
    if axis == "x":
        return (length, sy, sz)
    if axis == "y":
        return (sy, length, sz)
    if axis == "z":
        return (sy, sz, length)
    raise ValueError(f"Invalid axis: {axis}")


def _world_min_corner(
    spec: StructuralElementSpec, size: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (spec.position.x, spec.position.y, spec.position.z)


def _world_center(
    min_corner: tuple[float, float, float], size: tuple[float, float, float]
) -> tuple[float, float, float]:
    sx, sy, sz = size
    return (
        min_corner[0] + sx / 2,
        min_corner[1] + sy / 2,
        min_corner[2] + sz / 2,
    )


def _rotation_for_axis(axis: str) -> tuple[float, float, float]:
    """Euler XYZ radians so local length aligns with world axis (visual hint)."""
    return (0.0, 0.0, 0.0)


def spec_to_rendered(spec: StructuralElementSpec, index: int) -> RenderedStructuralElement:
    _, sy, sz = _section_bbox(spec)
    size = _orient_size(spec.length, sy, sz, spec.axis)
    min_corner = _world_min_corner(spec, size)
    center = _world_center(min_corner, size)
    shape_slug = spec.shape_type.lower().replace("-", "")

    return RenderedStructuralElement(
        id=f"{shape_slug}-{index}",
        shape_type=spec.shape_type,
        axis=spec.axis,
        position=center,
        rotation=_rotation_for_axis(spec.axis),
        size=size,
        height=spec.height,
        width=spec.width,
        thickness=spec.thickness,
        length=spec.length,
        color=SHAPE_COLORS.get(spec.shape_type),
    )


def generate_structural_elements(
    specs: list[StructuralElementSpec],
) -> ProjectState:
    if not specs:
        raise ValueError("elements array must contain at least one member")

    rendered = [spec_to_rendered(spec, i) for i, spec in enumerate(specs)]
    return ProjectState(version=2, elements=rendered)


def generate_structural_elements_from_dicts(
    raw_elements: list[dict],
) -> ProjectState:
    specs = [StructuralElementSpec.model_validate(item) for item in raw_elements]
    return generate_structural_elements(specs)

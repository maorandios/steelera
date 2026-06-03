"""
Parse add_structural_element tool args into flat millimeter-based JSON.

Backend coordinate convention: Y is vertical (structural height).
The frontend maps backend (x, y, z) → Three.js (x, z, y) with Y-up in the canvas.

Every member stores explicit connection nodes used for anchor snapping:
  - axis y (column): bottom [x,y,z], top [x, y+length, z]
  - axis x (beam):   start [x,y,z], end [x+length, y, z]
  - axis z (beam):   start [x,y,z], end [x, y, z+length]
"""

from core.anchoring import resolve_position_from_anchor
from core.member_nodes import compute_member_nodes
from catalog_loader import get_profile
from schemas.elements import (
    AddStructuralElementInput,
    ApplyMacroActionInput,
    ProjectElementMm,
    SectionDimensionsMm,
)

M_TO_MM = 1000.0
FT_TO_MM = 304.8
IN_TO_MM = 25.4

DEPTH_RATIO: dict[str, float] = {
    "I-beam": 1.2,
    "C-channel": 1.0,
    "Box": 1.0,
    "Pipe": 1.0,
}


def to_millimeters(value: float, unit: str) -> float:
    u = (unit or "auto").lower().strip()

    if u == "m":
        return value * M_TO_MM
    if u == "mm":
        return value
    if u == "ft":
        return value * FT_TO_MM
    if u == "in":
        return value * IN_TO_MM
    if u == "auto":
        if value < 20:
            return value * M_TO_MM
        return value

    raise ValueError(f"Unsupported unit: {unit}")


def parse_position_mm(position: dict[str, float], unit: str = "auto") -> dict[str, float]:
    return {
        "x": to_millimeters(float(position["x"]), unit),
        "y": to_millimeters(float(position["y"]), unit),
        "z": to_millimeters(float(position["z"]), unit),
    }


def section_depth_mm(shape_type: str, width_mm: float) -> float:
    ratio = DEPTH_RATIO.get(shape_type, 1.0)
    if shape_type == "Pipe":
        return width_mm
    return width_mm * ratio


def bounding_box_from_section(
    shape_type: str,
    length_mm: float,
    width_mm: float,
    depth_mm: float,
    axis: str = "y",
) -> dict[str, float]:
    if shape_type == "Pipe":
        d = max(width_mm, depth_mm)
        if axis == "x":
            return {"x": length_mm, "y": d, "z": d}
        if axis == "y":
            return {"x": d, "y": length_mm, "z": d}
        return {"x": d, "y": d, "z": length_mm}

    if axis == "x":
        return {"x": length_mm, "y": width_mm, "z": depth_mm}
    if axis == "y":
        return {"x": width_mm, "y": length_mm, "z": depth_mm}
    if axis == "z":
        return {"x": width_mm, "y": depth_mm, "z": length_mm}
    raise ValueError(f"Invalid axis: {axis}")


def _resolve_catalog_section(profile_name: str) -> SectionDimensionsMm:
    p = get_profile(profile_name)
    return SectionDimensionsMm(h=p["h"], b=p["b"], tw=p["tw"], tf=p["tf"])


def _build_element(
    *,
    element_index: int,
    slug: str,
    payload: AddStructuralElementInput,
    pos_mm: dict[str, float],
    length_mm: float,
    width_mm: float,
    depth_mm: float,
    section_source: str,
    profile_name: str | None,
    section: SectionDimensionsMm | None,
    anchor_id: str | None,
    anchor_pt: str | None,
) -> ProjectElementMm:
    size_mm = bounding_box_from_section(
        payload.shape_type, length_mm, width_mm, depth_mm, payload.axis
    )
    el = ProjectElementMm(
        id=f"{slug}-{element_index}",
        shape_type=payload.shape_type,
        position_mm=pos_mm,
        size_mm=size_mm,
        length_mm=length_mm,
        width_mm=width_mm,
        depth_mm=depth_mm,
        section_source=section_source,
        profile_name=profile_name,
        section_mm=section,
        axis=payload.axis,
        anchor_element_id=anchor_id,
        anchor_point=anchor_pt,
        nodes={},
    )
    return el.model_copy(update={"nodes": compute_member_nodes(el)})


def parse_add_structural_element(
    raw: dict,
    element_index: int,
    existing_elements: list[ProjectElementMm] | None = None,
    position_unit: str = "auto",
) -> ProjectElementMm:
    payload = AddStructuralElementInput.model_validate(raw)
    existing_elements = existing_elements or []

    length_mm = to_millimeters(payload.length.value, payload.length.unit)

    if payload.uses_anchor():
        pos_mm = resolve_position_from_anchor(
            payload,
            existing_elements,
            new_axis=payload.axis,
            new_length_mm=length_mm,
        )
        anchor_id = payload.anchor_element_id
        anchor_pt = payload.anchor_point
    else:
        pos_mm = parse_position_mm(
            {
                "x": payload.position.x,
                "y": payload.position.y,
                "z": payload.position.z,
            },
            unit=position_unit,
        )
        anchor_id = None
        anchor_pt = None

    if payload.uses_catalog():
        profile_key = payload.profile_name
        section = _resolve_catalog_section(profile_key)
        width_mm = section.b
        depth_mm = section.h
        return _build_element(
            element_index=element_index,
            slug=profile_key.lower(),
            payload=payload,
            pos_mm=pos_mm,
            length_mm=length_mm,
            width_mm=width_mm,
            depth_mm=depth_mm,
            section_source="catalog",
            profile_name=profile_key,
            section=section,
            anchor_id=anchor_id,
            anchor_pt=anchor_pt,
        )

    width_mm = to_millimeters(payload.width.value, payload.width.unit)
    depth_mm = section_depth_mm(payload.shape_type, width_mm)
    slug = payload.shape_type.lower().replace("-", "")

    return _build_element(
        element_index=element_index,
        slug=slug,
        payload=payload,
        pos_mm=pos_mm,
        length_mm=length_mm,
        width_mm=width_mm,
        depth_mm=depth_mm,
        section_source="parametric",
        profile_name=None,
        section=None,
        anchor_id=anchor_id,
        anchor_pt=anchor_pt,
    )


def _slug_from_element(element: ProjectElementMm) -> str:
    if element.profile_name:
        return element.profile_name.lower()
    return element.shape_type.lower().replace("-", "")


def _offset_vector_mm(axis: str, distance_mm: float) -> dict[str, float]:
    key = axis.upper()
    if key == "X":
        return {"x": distance_mm, "y": 0.0, "z": 0.0}
    if key == "Y":
        return {"x": 0.0, "y": distance_mm, "z": 0.0}
    if key == "Z":
        return {"x": 0.0, "y": 0.0, "z": distance_mm}
    raise ValueError(f"Invalid array axis: {axis}")


def _clone_element_at_offset(
    source: ProjectElementMm,
    element_index: int,
    offset_mm: dict[str, float],
) -> ProjectElementMm:
    slug = _slug_from_element(source)
    pos = source.position_mm
    new_pos = {
        "x": float(pos["x"]) + offset_mm["x"],
        "y": float(pos["y"]) + offset_mm["y"],
        "z": float(pos["z"]) + offset_mm["z"],
    }
    cloned = source.model_copy(
        update={
            "id": f"{slug}-{element_index}",
            "position_mm": new_pos,
            "anchor_element_id": None,
            "anchor_point": None,
        }
    )
    return cloned.model_copy(update={"nodes": compute_member_nodes(cloned)})


def _find_element(
    elements: list[ProjectElementMm],
    target_id: str,
) -> ProjectElementMm:
    for element in elements:
        if element.id == target_id:
            return element
    raise ValueError(f"Element not found: {target_id}")


def apply_macro_action(
    raw: dict,
    existing_elements: list[ProjectElementMm],
) -> tuple[list[ProjectElementMm], dict[str, object]]:
    payload = ApplyMacroActionInput.model_validate(raw)
    working = list(existing_elements)
    target = _find_element(working, payload.target_element_id)

    if payload.action_type == "DELETE":
        remaining = [element for element in working if element.id != payload.target_element_id]
        if len(remaining) == len(working):
            raise ValueError(f"Element not found: {payload.target_element_id}")
        return remaining, {
            "success": True,
            "action": "DELETE",
            "deleted_id": payload.target_element_id,
            "total_elements": len(remaining),
        }

    assert payload.spacing is not None
    assert payload.axis is not None
    assert payload.count is not None

    spacing_mm = to_millimeters(payload.spacing.value, payload.spacing.unit)
    created_ids: list[str] = []
    next_index = len(working)

    for copy_index in range(1, payload.count + 1):
        step = _offset_vector_mm(payload.axis, spacing_mm * copy_index)
        clone = _clone_element_at_offset(target, next_index, step)
        working.append(clone)
        created_ids.append(clone.id)
        next_index += 1

    return working, {
        "success": True,
        "action": "ARRAY",
        "source_id": target.id,
        "created_ids": created_ids,
        "count": payload.count,
        "spacing_mm": spacing_mm,
        "axis": payload.axis,
        "total_elements": len(working),
    }


def parse_add_structural_element_batch(
    raw_items: list[dict],
    start_index: int = 0,
    existing_elements: list[ProjectElementMm] | None = None,
    position_unit: str = "auto",
) -> list[ProjectElementMm]:
    results: list[ProjectElementMm] = []
    working = list(existing_elements or [])
    for i, item in enumerate(raw_items):
        el = parse_add_structural_element(
            item, start_index + i, existing_elements=working, position_unit=position_unit
        )
        results.append(el)
        working.append(el)
    return results

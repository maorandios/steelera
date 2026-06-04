"""
Parse add_structural_element tool args into flat millimeter-based JSON.

Backend coordinate convention: Y is vertical (structural height).
Shed macro plan: width along X, length along Z, height along Y.
The frontend maps backend (x, y, z) → Three.js (x, z, y) with Y-up in the canvas.

Every member stores explicit connection nodes used for anchor snapping:
  - axis y (column): bottom [x,y,z], top [x, y+length, z]
  - axis x (beam):   start [x,y,z], end [x+length, y, z]
  - axis z (beam):   start [x,y,z], end [x, y, z+length]
"""

import math
from typing import Any

from core.anchoring import resolve_position_from_anchor
from core.member_nodes import compute_member_nodes
from catalog_loader import CATALOG_PROFILE_NAMES, get_profile
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


CATALOG_MACRO_PROFILES = frozenset(CATALOG_PROFILE_NAMES)
PURLIN_PROFILE = "C150"
PURLIN_SHAPE = "C-channel"
PURLIN_SECTION_MM = {"h": 150.0, "b": 75.0, "tw": 4.0, "tf": 12.0}
RAFTER_HALF_DEPTH_MM = 100.0  # IPE200 h/2 — seat purlins on top flange


def _frame_positions_along(length_mm: float, spacing_mm: float) -> list[float]:
    """Bay positions from 0 through length inclusive."""
    positions: list[float] = []
    z = 0.0
    while z <= length_mm + 1e-6:
        positions.append(round(z, 3))
        if z >= length_mm - 1e-6:
            break
        z += spacing_mm
    if positions[-1] < length_mm - 1e-6:
        positions.append(round(length_mm, 3))
    return positions


def parse_bay_spans_mm(value: list[float] | str) -> list[float]:
    """
    Parse comma-separated bay spacings (mm): "5000, 5000" → [5000, 5000].
    Used for x_spans (width bays) and z_spans (portal frame bays along depth).
    """
    if isinstance(value, str):
        tokens = [part.strip() for part in value.split(",") if part.strip()]
        spans = [float(token) for token in tokens]
    else:
        spans = [float(step) for step in value]

    spans = [round(s, 3) for s in spans if s > 0]
    if not spans:
        raise ValueError("bay spans must contain at least one positive value (mm)")
    return spans


parse_x_spans_mm = parse_bay_spans_mm
parse_z_spans_mm = parse_bay_spans_mm


def resolve_x_spans_mm(
    x_spans: list[float] | str | None = None,
    width: float | None = None,
) -> list[float]:
    """Resolve shed X bays from x_spans and/or legacy width."""
    if x_spans is not None:
        return parse_bay_spans_mm(x_spans)
    if width is not None and width > 0:
        return [round(float(width), 3)]
    raise ValueError("x_spans or width must be provided")


def resolve_z_spans_mm(
    z_spans: list[float] | str | None = None,
    length: float | None = None,
    frame_spacing: float | None = None,
) -> list[float]:
    """Resolve portal-frame Z bays from z_spans and/or legacy length + frame_spacing."""
    if z_spans is not None:
        return parse_bay_spans_mm(z_spans)
    if length is not None and length > 0 and frame_spacing is not None and frame_spacing > 0:
        positions = _frame_positions_along(length, frame_spacing)
        return [
            round(positions[i] - positions[i - 1], 3)
            for i in range(1, len(positions))
        ]
    raise ValueError("z_spans or length with frame_spacing must be provided")


def cumulative_positions_from_spans(spans: list[float]) -> list[float]:
    """[3000, 4000, 3000] → [0, 3000, 7000, 10000]."""
    coords = [0.0]
    cumulative = 0.0
    for step in spans:
        cumulative += step
        coords.append(round(cumulative, 3))
    return coords


def _roof_elevation_at_x(
    x: float,
    total_width: float,
    ridge_x: float,
    eave_height: float,
    pitch_rad: float,
) -> float:
    """Gable roof surface Y at plan coordinate x (ridge at ridge_x)."""
    if x <= ridge_x + 1e-6:
        return eave_height + x * math.tan(pitch_rad)
    return eave_height + (total_width - x) * math.tan(pitch_rad)


def _column_height_at_x(
    x: float,
    total_width: float,
    ridge_x: float,
    eave_height: float,
    pitch_rad: float,
) -> float:
    """Column length: eave height at walls; interior columns meet the sloping rafters."""
    if x <= 1e-6 or x >= total_width - 1e-6:
        return eave_height
    return _roof_elevation_at_x(x, total_width, ridge_x, eave_height, pitch_rad)


def _macro_member_dict(
    *,
    element_id: str,
    assembly_id: str,
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
        "profile": profile,
        "position": [float(position[0]), float(position[1]), float(position[2])],
        "rotation": [float(rotation[0]), float(rotation[1]), float(rotation[2])],
        "alignment": alignment,
        "length": float(length),
        "axis": axis,
        "shape_type": shape_type,
        "nodes": nodes,
    }


def generate_shed_macro(
    assembly_id: str,
    height: float,
    roof_pitch_deg: float = 10.0,
    purlin_spacing: float = 1200.0,
    *,
    x_spans: list[float] | str,
    z_spans: list[float] | str,
    width: float | None = None,
    length: float | None = None,
    frame_spacing: float | None = None,
) -> list[dict[str, Any]]:
    """
    Parametric portal-frame shed (all dimensions in mm).

    - x_spans: structural bays across width → columns at cumulative X (0, 3k, 10k, …).
    - z_spans: portal frame bays along depth → frames at cumulative Z (0, 5k, 10k, …).
    - total_width = sum(x_spans), total_length = sum(z_spans).
    - Interior column heights follow the gable roof; ridge at total_width / 2.
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
    if purlin_spacing <= 0:
        raise ValueError("purlin_spacing must be positive")

    pitch_rad = math.radians(roof_pitch_deg)
    ridge_x = total_width / 2.0
    left_span = ridge_x
    right_span = total_width - ridge_x
    left_rise = left_span * math.tan(pitch_rad)
    right_rise = right_span * math.tan(pitch_rad)
    ridge_y = height + left_rise
    left_rafter_len = math.hypot(left_span, left_rise)
    right_rafter_len = math.hypot(right_span, right_rise)
    left_pitch_deg = math.degrees(math.atan2(left_rise, left_span)) if left_span > 0 else 0.0
    right_pitch_deg = (
        math.degrees(math.atan2(right_rise, right_span)) if right_span > 0 else 0.0
    )

    members: list[dict[str, Any]] = []
    first_frame_z = frame_zs[0]
    last_frame_z = frame_zs[-1]
    purlin_run_length = last_frame_z - first_frame_z

    for frame_index, z in enumerate(frame_zs):
        for x_index, x in enumerate(x_positions):
            col_height = _column_height_at_x(
                x, total_width, ridge_x, height, pitch_rad
            )
            col_top_y = col_height

            members.append(
                _macro_member_dict(
                    element_id=f"shed-col-{frame_index}-{x_index}",
                    assembly_id=assembly_id,
                    profile="HEA200",
                    position=[x, 0.0, z],
                    rotation=[0.0, 0.0, 0.0],
                    alignment="center",
                    length=col_height,
                    axis="y",
                    shape_type="I-beam",
                    nodes={
                        "bottom": [x, 0.0, z],
                        "top": [x, col_top_y, z],
                        "center": [x, col_top_y * 0.5, z],
                    },
                )
            )

        eave_y = height

        members.append(
            _macro_member_dict(
                element_id=f"shed-raf-L-{frame_index}",
                assembly_id=assembly_id,
                profile="IPE200",
                position=[0.0, eave_y, z],
                rotation=[0.0, 0.0, left_pitch_deg],
                alignment="center",
                length=left_rafter_len,
                axis="x",
                shape_type="I-beam",
                nodes={
                    "start": [0.0, eave_y, z],
                    "end": [ridge_x, ridge_y, z],
                    "center": [ridge_x * 0.5, (eave_y + ridge_y) * 0.5, z],
                },
            )
        )

        members.append(
            _macro_member_dict(
                element_id=f"shed-raf-R-{frame_index}",
                assembly_id=assembly_id,
                profile="IPE200",
                position=[total_width, eave_y, z],
                rotation=[0.0, 0.0, 180.0 - right_pitch_deg],
                alignment="center",
                length=right_rafter_len,
                axis="x",
                shape_type="I-beam",
                nodes={
                    "start": [total_width, eave_y, z],
                    "end": [ridge_x, ridge_y, z],
                    "center": [
                        (total_width + ridge_x) * 0.5,
                        (eave_y + ridge_y) * 0.5,
                        z,
                    ],
                },
            )
        )

    def _place_purlins_on_slope(
        suffix: str,
        rafter_len: float,
        pitch_deg: float,
        pitch_sign: float,
        x_at_eave: float,
        x_toward_ridge: float,
    ) -> None:
        nonlocal purlin_index
        slope_rad = math.radians(pitch_deg)
        slope_pos = 0.0
        while slope_pos <= rafter_len + 1e-6:
            t = slope_pos / rafter_len if rafter_len > 1e-6 else 0.0
            x_pos = x_at_eave + (x_toward_ridge - x_at_eave) * t
            elev_y = height + slope_pos * math.sin(slope_rad)
            normal_x = -math.sin(slope_rad) * pitch_sign
            normal_y = math.cos(slope_rad)
            seat_x = x_pos + RAFTER_HALF_DEPTH_MM * normal_x
            seat_y = elev_y + RAFTER_HALF_DEPTH_MM * normal_y
            members.append(
                _macro_member_dict(
                    element_id=f"shed-purl-{suffix}-{purlin_index}",
                    assembly_id=assembly_id,
                    profile=PURLIN_PROFILE,
                    position=[seat_x, seat_y, first_frame_z],
                    rotation=[pitch_sign * pitch_deg, 0.0, 0.0],
                    alignment="bottom",
                    length=purlin_run_length,
                    axis="z",
                    shape_type=PURLIN_SHAPE,
                    nodes={
                        "start": [seat_x, seat_y, first_frame_z],
                        "end": [seat_x, seat_y, last_frame_z],
                        "center": [
                            seat_x,
                            seat_y,
                            first_frame_z + purlin_run_length * 0.5,
                        ],
                    },
                )
            )
            if slope_pos >= rafter_len - 1e-6:
                break
            slope_pos += purlin_spacing
            purlin_index += 1

    purlin_index = 0
    _place_purlins_on_slope("L", left_rafter_len, left_pitch_deg, 1.0, 0.0, ridge_x)
    _place_purlins_on_slope(
        "R", right_rafter_len, right_pitch_deg, -1.0, total_width, ridge_x
    )

    return members


def macro_member_to_project_element(macro: dict[str, Any]) -> ProjectElementMm:
    """Convert a macro member dict into a full ProjectElementMm payload."""
    profile = str(macro["profile"]).strip().upper().replace(" ", "")
    axis = macro.get("axis", "y")
    length_mm = float(macro["length"])
    pos = macro["position"]
    alignment = macro.get("alignment", "center")
    rotation = macro.get("rotation", [0.0, 0.0, 0.0])
    shape_type = macro.get("shape_type") or (
        "I-beam" if profile in CATALOG_MACRO_PROFILES else PURLIN_SHAPE
    )

    if profile in CATALOG_MACRO_PROFILES:
        raw = {
            "shape_type": "I-beam",
            "length": {"value": length_mm, "unit": "mm"},
            "width": {"value": 0, "unit": "mm"},
            "profile_name": profile,
            "axis": axis,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "anchor_element_id": "NONE",
            "anchor_point": "NONE",
        }
        element = parse_add_structural_element(raw, 0, existing_elements=[])
    else:
        section = PURLIN_SECTION_MM
        raw = {
            "shape_type": shape_type,
            "length": {"value": length_mm, "unit": "mm"},
            "width": {"value": section["b"], "unit": "mm"},
            "profile_name": "NONE",
            "axis": axis,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "anchor_element_id": "NONE",
            "anchor_point": "NONE",
        }
        element = parse_add_structural_element(raw, 0, existing_elements=[])
        element = element.model_copy(
            update={
                "depth_mm": section["h"],
                "width_mm": section["b"],
                "section_mm": SectionDimensionsMm(**section),
            }
        )

    nodes = macro.get("nodes")
    if nodes:
        element = element.model_copy(update={"nodes": nodes})
    else:
        element = element.model_copy(update={"nodes": compute_member_nodes(element)})

    return element.model_copy(
        update={
            "id": macro["id"],
            "assembly_id": macro["assembly_id"],
            "alignment": alignment,
            "rotation_euler_deg": rotation,
        }
    )


def macro_members_to_project_elements(
    macro_members: list[dict[str, Any]],
) -> list[ProjectElementMm]:
    return [macro_member_to_project_element(member) for member in macro_members]


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

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
from catalog_loader import (
    CATALOG_PROFILE_NAMES,
    get_profile,
    has_profile,
    names_by_shape,
)
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


_SECTION_OPT_FIELDS = ("t", "d", "ro", "r", "lip")


def _resolve_catalog_section(profile_name: str) -> SectionDimensionsMm:
    p = get_profile(profile_name)
    kwargs: dict[str, float] = {
        "h": p["h"], "b": p["b"], "tw": p["tw"], "tf": p["tf"]
    }
    for opt in _SECTION_OPT_FIELDS:
        if opt in p and p[opt] is not None:
            kwargs[opt] = float(p[opt])
    return SectionDimensionsMm(**kwargs)


# Catalog shape string → frontend ShapeType. Most map 1:1; SHS is stored as RHS.
_CATALOG_SHAPE_TO_SHAPETYPE: dict[str, str] = {
    "I-beam": "I-beam",
    "C-channel": "C-channel",
    "Zed": "Zed",
    "RHS": "RHS",
    "SHS": "RHS",
    "CHS": "CHS",
    "Angle": "Angle",
    "Tee": "Tee",
    "Pipe": "Pipe",
    "Plate": "Plate",
}


def _shapetype_for_catalog(profile_name: str) -> str:
    shape = str(get_profile(profile_name).get("shape", "")).strip()
    return _CATALOG_SHAPE_TO_SHAPETYPE.get(shape, PURLIN_SHAPE)


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


# Any catalog I/H section (IPE, HEA/B/M, IPN, UB, UC) is extruded as an I-beam;
# channels/angles/hollow/rods use their own paths.
CATALOG_MACRO_PROFILES = names_by_shape("I-beam")
PURLIN_PROFILE = "C150"
PURLIN_SHAPE = "C-channel"
PURLIN_SECTION_MM = {"h": 150.0, "b": 75.0, "tw": 4.0, "tf": 12.0}
RAFTER_HALF_DEPTH_MM = 100.0  # IPE200 h/2 — seat purlins on top flange

# Haunch: a tapered cut of the rafter section, deep at the knee/apex, tapering to
# the rafter depth up-slope. Start (deep) depth = factor × rafter depth.
HAUNCH_RAFTER_PROFILE = "IPE200"
HAUNCH_START_DEPTH_FACTOR = 2.0
# Fly brace: small angle stay; render as a slender square stub.
FLY_BRACE_SIDE_MM = 60.0
# Base plate: square steel plate under each column foot.
BASE_PLATE_COLUMN_PROFILE = "HEA200"
BASE_PLATE_PLAN_FACTOR = 1.8  # × column flange width
BASE_PLATE_THICKNESS_MM = 25.0


def _macro_nodes_or_compute(
    element: ProjectElementMm, macro: dict[str, Any]
) -> ProjectElementMm:
    nodes = macro.get("nodes")
    if nodes:
        return element.model_copy(update={"nodes": nodes})
    return element.model_copy(update={"nodes": compute_member_nodes(element)})


def _special_macro_element(macro: dict[str, Any]) -> ProjectElementMm | None:
    """Plate / haunch members bypass the standard catalog extrusion paths."""
    et = macro.get("element_type")
    if et not in ("base_plate", "haunch"):
        return None

    pos = macro["position"]
    length_mm = float(macro["length"])
    axis = macro.get("axis", "x")
    rotation = macro.get("rotation", [0.0, 0.0, 0.0])
    common = {
        "id": macro["id"],
        "assembly_id": macro["assembly_id"],
        "position_mm": {"x": pos[0], "y": pos[1], "z": pos[2]},
        "axis": axis,
        "alignment": macro.get("alignment", "center"),
        "rotation_euler_deg": rotation,
        "element_type": et,
        "section_source": "parametric",
        "profile_name": None,
        "section_mm": None,
    }

    if et == "base_plate":
        col = get_profile(BASE_PLATE_COLUMN_PROFILE)
        plan = max(length_mm, col["b"] * BASE_PLATE_PLAN_FACTOR)
        plate_profile = str(macro.get("profile") or "").strip().upper().replace(" ", "")
        if has_profile(plate_profile):
            thickness = float(get_profile(plate_profile).get("t", BASE_PLATE_THICKNESS_MM))
        else:
            thickness = BASE_PLATE_THICKNESS_MM
        el = ProjectElementMm(
            shape_type="Plate",
            size_mm={"x": plan, "y": thickness, "z": plan},
            length_mm=plan,
            width_mm=plan,
            depth_mm=thickness,
            **common,
        )
        return _macro_nodes_or_compute(el, macro)

    if et == "haunch":
        raf = get_profile(HAUNCH_RAFTER_PROFILE)
        start_depth = raf["h"] * HAUNCH_START_DEPTH_FACTOR
        end_depth = raf["h"]
        width = raf["b"]
        el = ProjectElementMm(
            shape_type="Haunch",
            size_mm={"x": length_mm, "y": start_depth, "z": width},
            length_mm=length_mm,
            width_mm=width,
            depth_mm=start_depth,
            taper_end_depth_mm=end_depth,
            alignment="center",
            **{k: v for k, v in common.items() if k != "alignment"},
        )
        return _macro_nodes_or_compute(el, macro)

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


# Shed macro geometry lives in shed_geometry.py (re-exported below).


def macro_member_to_project_element(macro: dict[str, Any]) -> ProjectElementMm:
    """Convert a macro member dict into a full ProjectElementMm payload."""
    special = _special_macro_element(macro)
    if special is not None:
        return special

    profile = str(macro["profile"]).strip().upper().replace(" ", "")
    axis = macro.get("axis", "y")
    length_mm = float(macro["length"])
    pos = macro["position"]
    alignment = macro.get("alignment", "center")
    rotation = macro.get("rotation", [0.0, 0.0, 0.0])
    is_catalog = has_profile(profile)
    shape_type = macro.get("shape_type") or (
        "I-beam"
        if profile in CATALOG_MACRO_PROFILES
        else (_shapetype_for_catalog(profile) if is_catalog else PURLIN_SHAPE)
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
        # Purlins/girts/rods/secondary steel: pull real dims from the catalog when
        # the profile is known; otherwise fall back to the legacy C150 stand-in.
        if is_catalog:
            section_obj = _resolve_catalog_section(profile)
            sec_h, sec_b = section_obj.h, section_obj.b
        else:
            section_obj = SectionDimensionsMm(**PURLIN_SECTION_MM)
            sec_h, sec_b = PURLIN_SECTION_MM["h"], PURLIN_SECTION_MM["b"]
        raw = {
            "shape_type": shape_type,
            "length": {"value": length_mm, "unit": "mm"},
            "width": {"value": sec_b, "unit": "mm"},
            "profile_name": "NONE",
            "axis": axis,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "anchor_element_id": "NONE",
            "anchor_point": "NONE",
        }
        element = parse_add_structural_element(raw, 0, existing_elements=[])
        size = bounding_box_from_section(shape_type, length_mm, sec_b, sec_h, axis)
        element = element.model_copy(
            update={
                "size_mm": size,
                "depth_mm": sec_h,
                "width_mm": sec_b,
                "section_mm": section_obj,
                "section_source": "catalog" if is_catalog else "parametric",
                "profile_name": profile if is_catalog else None,
            }
        )

    nodes = macro.get("nodes")
    if nodes:
        element = element.model_copy(update={"nodes": nodes})
    else:
        element = element.model_copy(update={"nodes": compute_member_nodes(element)})

    update: dict[str, Any] = {
        "id": macro["id"],
        "assembly_id": macro["assembly_id"],
        "alignment": alignment,
        "rotation_euler_deg": rotation,
    }
    if macro.get("element_type"):
        update["element_type"] = macro["element_type"]
    return element.model_copy(update=update)


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

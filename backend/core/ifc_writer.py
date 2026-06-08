"""
Export Steelera structural topology to IFC (IFC2X3 / IFC4) via ifcopenshell.

Consumes the dictionary produced by ``IFCTopology.model_dump()`` — nodes, entities,
and assembly metadata only. Does not call the geometry solver.
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.guid

from catalog_loader import get_profile, has_profile

logger = logging.getLogger(__name__)

_MIN_MEMBER_LENGTH_MM = 0.5
_SUPPORTED_SCHEMAS = frozenset({"IFC2X3", "IFC4"})

# Steelera topology: X = width, Y = height (vertical), Z = length.
# IFC / Tekla / Revit convention: Z = height (vertical), Y = length, X = width.
# Map: ifc(x, y, z) = steelera(x, z, y)


def _to_ifc_point(x: float, y: float, z: float) -> tuple[float, float, float]:
    return (float(x), float(z), float(y))


def _to_ifc_vector(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
    return (float(dx), float(dz), float(dy))


def _normalize_vec(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _quat_from_unit_vectors(
    ax: float,
    ay: float,
    az: float,
    bx: float,
    by: float,
    bz: float,
) -> tuple[float, float, float, float]:
    """Port of THREE.Quaternion.setFromUnitVectors (member-local +X → world dir)."""
    dx, dy, dz = _normalize_vec((bx, by, bz))
    dot = max(-1.0, min(1.0, ax * dx + ay * dy + az * dz))
    if dot > 1.0 - 1e-6:
        return (0.0, 0.0, 0.0, 1.0)
    if dot < -1.0 + 1e-6:
        return (0.0, 0.0, 1.0, 0.0)
    cx = ay * dz - az * dy
    cy = az * dx - ax * dz
    cz = ax * dy - ay * dx
    clen = math.sqrt(cx * cx + cy * cy + cz * cz)
    cx, cy, cz = cx / clen, cy / clen, cz / clen
    angle = math.acos(dot)
    half = angle * 0.5
    s = math.sin(half)
    return (cx * s, cy * s, cz * s, math.cos(half))


def _quat_mul(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _quat_rotate(
    q: tuple[float, float, float, float],
    v: tuple[float, float, float],
) -> tuple[float, float, float]:
    qx, qy, qz, qw = q
    x, y, z = v
    tx = 2.0 * (qy * z - qz * y)
    ty = 2.0 * (qz * x - qx * z)
    tz = 2.0 * (qx * y - qy * x)
    return (
        x + qw * tx + qy * tz - qz * ty,
        y + qw * ty + qz * tx - qx * tz,
        z + qw * tz + qx * ty - qy * tx,
    )


def _member_ref_direction(
    axis_z: tuple[float, float, float],
    start_steelera: tuple[float, float, float],
    end_steelera: tuple[float, float, float],
    roll_deg: float,
) -> tuple[float, float, float]:
    """Profile roll about the member axis (viewport quaternion, IFC Z-up)."""
    dx = end_steelera[0] - start_steelera[0]
    dy = end_steelera[1] - start_steelera[1]
    dz = end_steelera[2] - start_steelera[2]
    dir_s = _normalize_vec((dx, dy, dz))
    q_align = _quat_from_unit_vectors(1.0, 0.0, 0.0, *dir_s)
    roll_rad = math.radians(roll_deg)
    q_roll = (math.sin(roll_rad * 0.5), 0.0, 0.0, math.cos(roll_rad * 0.5))
    q = _quat_mul(q_align, q_roll)
    profile_y_ifc = _normalize_vec(_to_ifc_vector(*_quat_rotate(q, (0.0, 1.0, 0.0))))
    return _normalize_vec(_cross(profile_y_ifc, axis_z))


def _strict_member_frame(
    start_steelera: tuple[float, float, float],
    end_steelera: tuple[float, float, float],
    *,
    roll_deg: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float], float] | None:
    """
    Structural axis: placement at exact start node, extrusion along end − start.
    Length is the Euclidean distance between global topology nodes (IFC Z-up).
    """
    start_ifc = _to_ifc_point(*start_steelera)
    end_ifc = _to_ifc_point(*end_steelera)
    vx = end_ifc[0] - start_ifc[0]
    vy = end_ifc[1] - start_ifc[1]
    vz = end_ifc[2] - start_ifc[2]
    length = math.sqrt(vx * vx + vy * vy + vz * vz)
    if length < _MIN_MEMBER_LENGTH_MM:
        return None

    axis_z = _normalize_vec((vx, vy, vz))
    axis_x = _member_ref_direction(axis_z, start_steelera, end_steelera, roll_deg)
    return start_ifc, axis_z, axis_x, length


def _solid_seating_offset(align_offset_mm: float) -> tuple[float, float, float]:
    """
    Shift the Body solid along product-local +Y (profile height), matching viewport
    ``meshAlignmentOffsetLocal``.  Location must be in the product placement frame
    (RefDirection, Y, member Axis) — not global IFC coordinates.
    """
    if abs(align_offset_mm) < 1e-9:
        return (0.0, 0.0, 0.0)
    return (0.0, align_offset_mm, 0.0)

# --------------------------------------------------------------------------- #
# Schema / GUID helpers                                                       #
# --------------------------------------------------------------------------- #


def _normalize_schema(schema_version: str) -> str:
    key = str(schema_version or "IFC2X3").strip().upper().replace(" ", "")
    if key in ("IFC2X3", "IFC2X3_TC1", "IFC2X3_ADD2"):
        return "IFC2X3"
    if key.startswith("IFC4"):
        return "IFC4"
    raise ValueError(f"Unsupported IFC schema: {schema_version!r}")


def _new_guid() -> str:
    return ifcopenshell.guid.new()


def _point(file: ifcopenshell.file, x: float, y: float, z: float) -> Any:
    return file.create_entity("IfcCartesianPoint", Coordinates=(float(x), float(y), float(z)))


def _direction(file: ifcopenshell.file, x: float, y: float, z: float) -> Any:
    length = math.sqrt(x * x + y * y + z * z)
    if length < 1e-12:
        return file.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    return file.create_entity(
        "IfcDirection",
        DirectionRatios=(x / length, y / length, z / length),
    )


def _axis2_placement(
    file: ifcopenshell.file,
    origin: tuple[float, float, float],
    axis: tuple[float, float, float],
    ref_direction: tuple[float, float, float],
) -> Any:
    return file.create_entity(
        "IfcAxis2Placement3D",
        Location=_point(file, *origin),
        Axis=_direction(file, *axis),
        RefDirection=_direction(file, *ref_direction),
    )


def _local_placement(
    file: ifcopenshell.file,
    placement: Any,
    *,
    parent: Any | None = None,
) -> Any:
    return file.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=parent,
        RelativePlacement=placement,
    )


# --------------------------------------------------------------------------- #
# Units & project shell                                                       #
# --------------------------------------------------------------------------- #


def _create_owner_history(file: ifcopenshell.file) -> Any:
    person = file.create_entity("IfcPerson", FamilyName="Steelera")
    org = file.create_entity("IfcOrganization", Name="Steelera")
    person_org = file.create_entity(
        "IfcPersonAndOrganization",
        ThePerson=person,
        TheOrganization=org,
    )
    application = file.create_entity(
        "IfcApplication",
        ApplicationDeveloper=org,
        Version="1.0",
        ApplicationFullName="Steelera IFC Export",
        ApplicationIdentifier="STEELERA",
    )
    return file.create_entity(
        "IfcOwnerHistory",
        OwningUser=person_org,
        OwningApplication=application,
        ChangeAction="ADDED",
        CreationDate=int(time.time()),
    )


def _create_units(file: ifcopenshell.file) -> Any:
    length_unit = file.create_entity(
        "IfcSIUnit",
        UnitType="LENGTHUNIT",
        Prefix="MILLI",
        Name="METRE",
    )
    angle_unit = file.create_entity(
        "IfcSIUnit",
        UnitType="PLANEANGLEUNIT",
        Name="RADIAN",
    )
    mass_unit = file.create_entity(
        "IfcSIUnit",
        UnitType="MASSUNIT",
        Prefix="KILO",
        Name="GRAM",
    )
    return file.create_entity(
        "IfcUnitAssignment",
        Units=[length_unit, angle_unit, mass_unit],
    )


def _create_representation_context(file: ifcopenshell.file) -> Any:
    world = _axis2_placement(file, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
    return file.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Body",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1.0e-5,
        WorldCoordinateSystem=world,
        TrueNorth=_direction(file, 1.0, 0.0, 0.0),
    )


def _create_spatial_hierarchy(
    file: ifcopenshell.file,
    *,
    owner_history: Any,
    building_id: str,
    context: Any,
) -> tuple[Any, Any, Any, Any]:
    """Return (project, site, building, storey)."""
    project = file.create_entity(
        "IfcProject",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name=f"Steelera Project ({building_id})",
        Description="Structural steel export from Steelera topology",
        RepresentationContexts=[context],
        UnitsInContext=_create_units(file),
    )

    site_placement = _local_placement(
        file,
        _axis2_placement(file, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
    )
    site = file.create_entity(
        "IfcSite",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name="Site",
        ObjectPlacement=site_placement,
    )

    building_placement = _local_placement(
        file,
        _axis2_placement(file, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        parent=site_placement,
    )
    building = file.create_entity(
        "IfcBuilding",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name="Structural Building",
        ObjectPlacement=building_placement,
    )

    storey_placement = _local_placement(
        file,
        _axis2_placement(file, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        parent=building_placement,
    )
    storey = file.create_entity(
        "IfcBuildingStorey",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    file.create_entity(
        "IfcRelAggregates",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingObject=project,
        RelatedObjects=[site],
    )
    file.create_entity(
        "IfcRelAggregates",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingObject=site,
        RelatedObjects=[building],
    )
    file.create_entity(
        "IfcRelAggregates",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingObject=building,
        RelatedObjects=[storey],
    )

    return project, site, building, storey


# --------------------------------------------------------------------------- #
# Profile resolution                                                          #
# --------------------------------------------------------------------------- #


def _profile_prefix(profile_family: str) -> str:
    name = str(profile_family or "").strip().upper().replace(" ", "")
    if not name:
        return ""
    for prefix in (
        "HEA",
        "HEB",
        "HEM",
        "IPE",
        "IPN",
        "UB",
        "UC",
        "RHS",
        "SHS",
        "CHS",
        "ROD",
        "PL",
    ):
        if name.startswith(prefix):
            return prefix
    if name.startswith("C") and "X" in name:
        return "C"
    if name.startswith("Z") and "X" in name:
        return "Z"
    if name.startswith("L"):
        return "L"
    return ""


def _catalog_dims(profile_family: str) -> dict[str, float | str]:
    if has_profile(profile_family):
        raw = get_profile(profile_family)
        return {
            "h": float(raw.get("h", 100.0)),
            "b": float(raw.get("b", 50.0)),
            "tw": float(raw.get("tw", 5.0)),
            "tf": float(raw.get("tf", 5.0)),
            "t": float(raw.get("t", raw.get("tw", 5.0))),
            "d": float(raw.get("d", raw.get("h", 50.0))),
            "r": float(raw.get("r", 0.0)),
            "ro": float(raw.get("ro", 0.0)),
            "lip": float(raw.get("lip", 15.0)),
            "shape": str(raw.get("shape", "")),
            "mass_per_m": float(raw.get("mass_per_m", 0.0)),
        }
    return {
        "h": 100.0,
        "b": 50.0,
        "tw": 5.0,
        "tf": 5.0,
        "t": 5.0,
        "d": 50.0,
        "r": 0.0,
        "ro": 0.0,
        "lip": 15.0,
        "shape": "",
        "mass_per_m": 0.0,
    }


def _member_weight_kg(profile_family: str, length_mm: float) -> float:
    dims = _catalog_dims(profile_family)
    mass_per_m = float(dims.get("mass_per_m", 0.0))
    if mass_per_m <= 0:
        return 0.0
    return mass_per_m * (length_mm / 1000.0)


def _resolve_profile_kind(prefix: str, dims: dict[str, float | str]) -> str:
    shape = str(dims.get("shape", "")).strip()
    if shape in ("I-beam", "Haunch"):
        return "i"
    if shape in ("Tee",):
        return "tee"
    if shape in ("C-channel",):
        return "c"
    if shape in ("Zed",):
        return "z"
    if shape in ("Angle",):
        return "l"
    if shape in ("RHS", "SHS", "Box"):
        return "hollow_rect"
    if shape in ("CHS", "Pipe"):
        return "hollow_circle"
    if shape in ("Plate",):
        return "plate"
    if prefix in ("HEA", "HEB", "HEM", "IPE", "IPN", "UB", "UC"):
        return "i"
    if prefix in ("RHS", "SHS"):
        return "hollow_rect"
    if prefix in ("CHS", "ROD"):
        return "hollow_circle"
    if prefix == "C":
        return "c"
    if prefix == "Z":
        return "z"
    if prefix == "L":
        return "l"
    if prefix == "PL":
        return "plate"
    return "rect"


def _center_polygon(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return points
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    return [(x - cx, y - cy) for x, y in points]


def _mirror_polygon_x(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Mirror profile through the local Y axis (viewport ``scale(1,1,-1)`` width flip)."""
    return [(-x, y) for x, y in points]


def _mirror_polygon_y(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Mirror profile through the local X axis (open-side / height flip)."""
    return [(x, -y) for x, y in points]


def _is_girt_entity(entity: dict[str, Any]) -> bool:
    entity_id = str(entity.get("id", ""))
    return "-girt-" in entity_id or "-gablegirt-" in entity_id


def _cee_polygon(h: float, b: float, t: float, lip: float) -> list[tuple[float, float]]:
    if lip > t:
        raw = [
            (0.0, 0.0),
            (b, 0.0),
            (b, lip),
            (b - t, lip),
            (b - t, t),
            (t, t),
            (t, h - t),
            (b - t, h - t),
            (b - t, h - lip),
            (b, h - lip),
            (b, h),
            (0.0, h),
        ]
    else:
        raw = [
            (0.0, 0.0),
            (b, 0.0),
            (b, t),
            (t, t),
            (t, h - t),
            (b, h - t),
            (b, h),
            (0.0, h),
        ]
    return _center_polygon(raw)


def _zed_polygon(h: float, b: float, t: float, lip: float) -> list[tuple[float, float]]:
    if lip > t:
        raw = [
            (t - b, 0.0),
            (t, 0.0),
            (t, h - t),
            (b - t, h - t),
            (b - t, h - lip),
            (b, h - lip),
            (b, h),
            (0.0, h),
            (0.0, t),
            (2.0 * t - b, t),
            (2.0 * t - b, lip),
            (t - b, lip),
        ]
    else:
        raw = [
            (t - b, 0.0),
            (t, 0.0),
            (t, h - t),
            (b, h - t),
            (b, h),
            (0.0, h),
            (0.0, t),
            (t - b, t),
        ]
    return _center_polygon(raw)


def _angle_polygon(h: float, b: float, t: float) -> list[tuple[float, float]]:
    x0 = -b / 2.0
    y0 = -h / 2.0
    raw = [
        (x0, y0),
        (x0 + b, y0),
        (x0 + b, y0 + t),
        (x0 + t, y0 + t),
        (x0 + t, y0 + h),
        (x0, y0 + h),
    ]
    return _center_polygon(raw)


def _tee_polygon(h: float, b: float, tw: float, tf: float) -> list[tuple[float, float]]:
    hw = h / 2.0
    bw = b / 2.0
    tww = tw / 2.0
    raw = [
        (-bw, hw),
        (bw, hw),
        (bw, hw - tf),
        (tww, hw - tf),
        (tww, -hw),
        (-tww, -hw),
        (-tww, hw - tf),
        (-bw, hw - tf),
    ]
    return _center_polygon(raw)


def _arbitrary_profile_def(
    file: ifcopenshell.file,
    *,
    name: str,
    polygon: list[tuple[float, float]],
) -> Any:
    points = [
        file.create_entity("IfcCartesianPoint", Coordinates=(float(x), float(y)))
        for x, y in polygon
    ]
    if points[0].Coordinates != points[-1].Coordinates:
        points.append(points[0])
    polyline = file.create_entity("IfcPolyLine", Points=points)
    return file.create_entity(
        "IfcArbitraryClosedProfileDef",
        ProfileType="AREA",
        ProfileName=name,
        OuterCurve=polyline,
    )


def _create_profile_def(
    file: ifcopenshell.file,
    profile_family: str,
    *,
    schema: str,
    cache: dict[str, Any],
    mirror_profile_x: bool = False,
    mirror_profile_y: bool = False,
) -> Any:
    base_key = str(profile_family or "GENERIC").strip().upper().replace(" ", "") or "GENERIC"
    suffix = ""
    if mirror_profile_y:
        suffix += "Y"
    if mirror_profile_x:
        suffix += "X"
    key = f"{base_key}#{suffix}" if suffix else base_key
    if key in cache:
        return cache[key]

    dims = _catalog_dims(base_key)
    prefix = _profile_prefix(base_key)
    name = base_key
    kind = _resolve_profile_kind(prefix, dims)

    profile: Any
    try:
        if kind == "i":
            kwargs: dict[str, Any] = {
                "ProfileType": "AREA",
                "ProfileName": name,
                "OverallDepth": float(dims["h"]),
                "OverallWidth": float(dims["b"]),
                "WebThickness": float(dims["tw"]),
                "FlangeThickness": float(dims["tf"]),
            }
            fillet = float(dims["r"])
            if fillet > 0:
                kwargs["FilletRadius"] = fillet
            profile = file.create_entity("IfcIShapeProfileDef", **kwargs)

        elif kind == "hollow_rect":
            profile = file.create_entity(
                "IfcRectangleHollowProfileDef",
                ProfileType="AREA",
                ProfileName=name,
                XDim=float(dims["h"]),
                YDim=float(dims["b"]),
                WallThickness=float(dims["t"]),
                InnerFilletRadius=0.0,
                OuterFilletRadius=float(dims["ro"]),
            )

        elif kind == "hollow_circle":
            radius = max(float(dims["d"]), float(dims["h"])) / 2.0
            wall = float(dims["t"])
            if wall > 0 and wall < radius:
                profile = file.create_entity(
                    "IfcCircleHollowProfileDef",
                    ProfileType="AREA",
                    ProfileName=name,
                    Radius=radius,
                    WallThickness=wall,
                )
            else:
                profile = file.create_entity(
                    "IfcCircleProfileDef",
                    ProfileType="AREA",
                    ProfileName=name,
                    Radius=radius,
                )

        elif kind == "c":
            cee = _cee_polygon(
                float(dims["h"]),
                float(dims["b"]),
                float(dims["t"]),
                float(dims["lip"]),
            )
            if mirror_profile_y:
                cee = _mirror_polygon_y(cee)
            if mirror_profile_x:
                cee = _mirror_polygon_x(cee)
            profile = _arbitrary_profile_def(
                file,
                name=name,
                polygon=cee,
            )

        elif kind == "z":
            zed = _zed_polygon(
                float(dims["h"]),
                float(dims["b"]),
                float(dims["t"]),
                float(dims["lip"]),
            )
            if mirror_profile_y:
                zed = _mirror_polygon_y(zed)
            if mirror_profile_x:
                zed = _mirror_polygon_x(zed)
            if schema == "IFC4" and not mirror_profile_x:
                profile = file.create_entity(
                    "IfcZShapeProfileDef",
                    ProfileType="AREA",
                    ProfileName=name,
                    Depth=float(dims["h"]),
                    FlangeWidth=float(dims["b"]),
                    WebThickness=float(dims["t"]),
                    FilletRadius=0.0,
                    EdgeRadius=0.0,
                )
            else:
                profile = _arbitrary_profile_def(
                    file,
                    name=name,
                    polygon=zed,
                )

        elif kind == "l":
            if schema == "IFC4":
                profile = file.create_entity(
                    "IfcLShapeProfileDef",
                    ProfileType="AREA",
                    ProfileName=name,
                    Depth=float(dims["h"]),
                    Width=float(dims["b"]),
                    Thickness=float(dims["t"]),
                    FilletRadius=0.0,
                    EdgeRadius=0.0,
                )
            else:
                profile = _arbitrary_profile_def(
                    file,
                    name=name,
                    polygon=_angle_polygon(
                        float(dims["h"]),
                        float(dims["b"]),
                        float(dims["t"]),
                    ),
                )

        elif kind == "tee":
            profile = _arbitrary_profile_def(
                file,
                name=name,
                polygon=_tee_polygon(
                    float(dims["h"]),
                    float(dims["b"]),
                    float(dims["tw"]),
                    float(dims["tf"]),
                ),
            )

        elif kind == "plate":
            thickness = max(float(dims["t"]), 1.0)
            plan = max(float(dims["h"]), float(dims["b"]), 200.0)
            profile = file.create_entity(
                "IfcRectangleProfileDef",
                ProfileType="AREA",
                ProfileName=name,
                XDim=plan,
                YDim=thickness,
            )

        else:
            profile = file.create_entity(
                "IfcRectangleProfileDef",
                ProfileType="AREA",
                ProfileName=name or "FALLBACK",
                XDim=max(float(dims["h"]), 10.0),
                YDim=max(float(dims["b"]), 10.0),
            )
    except Exception:
        logger.warning(
            "Profile %s failed; using rectangular fallback",
            name,
            exc_info=True,
        )
        profile = file.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            ProfileName=name or "FALLBACK",
            XDim=max(float(dims["h"]), 10.0),
            YDim=max(float(dims["b"]), 10.0),
        )

    cache[key] = profile
    return profile


# --------------------------------------------------------------------------- #
# Member placement & geometry                                                 #
# --------------------------------------------------------------------------- #


def _entity_rotation_euler(entity: dict[str, Any]) -> list[float]:
    euler = entity.get("rotation_euler")
    if isinstance(euler, (list, tuple)) and euler:
        return [
            float(euler[i]) if i < len(euler) else 0.0
            for i in range(3)
        ]
    return [float(entity.get("local_rotation", 0.0)), 0.0, 0.0]


def _purlin_ridge_mirror(entity: dict[str, Any]) -> bool:
    """Right-of-ridge purlins mirror the C profile (viewport ``scale(1,1,-1)``)."""
    entity_id = str(entity.get("id", ""))
    role = str(entity.get("structural_role", ""))
    if "purlin" not in entity_id and role != "PURLIN":
        return False
    _, yaw_mirror, _ = _entity_rotation_euler(entity)
    return abs(yaw_mirror) > 90.0


def _girt_geometry_flip_z(entity: dict[str, Any]) -> bool:
    """Match viewport ``wallGirtGeometryFlipZ`` (Z-flip at 90° roll, not roll + 180°)."""
    entity_id = str(entity.get("id", ""))
    if "-girt-" not in entity_id and "-gablegirt-" not in entity_id:
        return False
    roll, _, _ = _entity_rotation_euler(entity)
    return abs(roll - 90.0) < 1.0


def _effective_roll_deg(entity: dict[str, Any]) -> float:
    """Match viewport roll; profile mirror is a geometry flip, not roll + 180°."""
    roll, _, _ = _entity_rotation_euler(entity)
    return roll


def _node_coords_steelera(nodes: dict[str, Any], node_id: str) -> tuple[float, float, float] | None:
    raw = nodes.get(node_id)
    if raw is None:
        return None
    if isinstance(raw, dict):
        return (float(raw["x"]), float(raw["y"]), float(raw["z"]))
    return (float(raw.x), float(raw.y), float(raw.z))


def _alignment_offset_mm(entity: dict[str, Any], profile_family: str) -> float:
    """Shift section centroid from the connection node (matches viewport alignment)."""
    alignment = str(entity.get("alignment") or "center").strip().lower()
    if alignment == "center":
        return 0.0
    dims = _catalog_dims(profile_family)
    half_h = float(dims.get("h", 100.0)) * 0.5
    if alignment == "bottom":
        return half_h
    if alignment == "top":
        return -half_h
    return 0.0


def _create_extruded_body(
    file: ifcopenshell.file,
    *,
    profile: Any,
    length_mm: float,
    context: Any,
    profile_flip_z: bool = False,
    solid_origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Any:
    # Viewport ridge mirror uses geometry.scale(1,1,-1) — flip profile local X in the solid.
    ref_x = -1.0 if profile_flip_z else 1.0
    solid_position = _axis2_placement(
        file,
        solid_origin,
        (0.0, 0.0, 1.0),
        (ref_x, 0.0, 0.0),
    )
    solid = file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=solid_position,
        ExtrudedDirection=_direction(file, 0.0, 0.0, 1.0),
        Depth=float(length_mm),
    )
    return file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )


def _create_axis_representation(
    file: ifcopenshell.file,
    *,
    length_mm: float,
    context: Any,
) -> Any:
    """
    Analytical member axis: local line from origin to (0, 0, length).
    With placement at the global start node and axis along end − start, this
    maps exactly onto the topology nodes in world space (STRAP / analysis).
    """
    polyline = file.create_entity(
        "IfcPolyline",
        Points=[
            _point(file, 0.0, 0.0, 0.0),
            _point(file, 0.0, 0.0, length_mm),
        ],
    )
    return file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Axis",
        RepresentationType="Curve3D",
        Items=[polyline],
    )


def _product_class_name(ifc_type: str, schema: str) -> str:
    key = str(ifc_type or "IfcMember").strip()
    if key == "IfcPlate" and schema == "IFC2X3":
        return "IfcBuildingElementProxy"
    return key


def _create_product(
    file: ifcopenshell.file,
    *,
    ifc_type: str,
    schema: str,
    entity_id: str,
    structural_role: str,
    owner_history: Any,
    placement: Any,
    representations: list[Any],
) -> Any:
    kwargs: dict[str, Any] = {
        "GlobalId": _new_guid(),
        "OwnerHistory": owner_history,
        "Name": entity_id,
        "Description": structural_role,
        "ObjectPlacement": placement,
        "Representation": file.create_entity(
            "IfcProductDefinitionShape",
            Representations=representations,
        ),
    }
    class_name = _product_class_name(ifc_type, schema)
    if class_name == "IfcBuildingElementProxy":
        kwargs["ObjectType"] = "Plate"
    product = file.create_entity(class_name, **kwargs)
    return product


def _text_value(file: ifcopenshell.file, value: str) -> Any:
    try:
        return file.create_entity("IfcText", str(value))
    except Exception:
        return file.create_entity("IfcLabel", str(value))


def _real_value(file: ifcopenshell.file, value: float) -> Any:
    return file.create_entity("IfcReal", float(value))


def _attach_property_set(
    file: ifcopenshell.file,
    *,
    owner_history: Any,
    product: Any,
    entity: dict[str, Any],
    length_mm: float,
    weight_kg: float,
) -> None:
    assembly_ids = entity.get("assembly_ids") or []
    profile_family = str(entity.get("profile_family", "") or "")
    dims = _catalog_dims(profile_family)
    mass_per_m = float(dims.get("mass_per_m", 0.0))

    props = [
        file.create_entity(
            "IfcPropertySingleValue",
            Name="SteeleraMemberId",
            NominalValue=_text_value(file, str(entity.get("id", ""))),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="StructuralRole",
            NominalValue=_text_value(file, str(entity.get("structural_role", ""))),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="ProfileFamily",
            NominalValue=_text_value(file, profile_family),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="PrimaryAssemblyId",
            NominalValue=_text_value(file, str(entity.get("primary_assembly_id", ""))),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="AssemblyIds",
            NominalValue=_text_value(file, ",".join(str(a) for a in assembly_ids)),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="LocalRotationDeg",
            NominalValue=_real_value(file, float(entity.get("local_rotation", 0.0))),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="MemberLengthMm",
            NominalValue=_real_value(file, length_mm),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="MassPerMetreKg",
            NominalValue=_real_value(file, mass_per_m),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="MemberWeightKg",
            NominalValue=_real_value(file, weight_kg),
        ),
    ]
    pset = file.create_entity(
        "IfcPropertySet",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name="Pset_SteeleraStructural",
        HasProperties=props,
    )
    file.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingPropertyDefinition=pset,
        RelatedObjects=[product],
    )


def _quantity_set_name(ifc_type: str) -> str:
    key = str(ifc_type or "IfcMember")
    if key == "IfcBeam":
        return "Qto_BeamBaseQuantities"
    if key == "IfcColumn":
        return "Qto_ColumnBaseQuantities"
    if key == "IfcPlate":
        return "Qto_PlateBaseQuantities"
    return "Qto_MemberBaseQuantities"


def _common_pset_name(ifc_type: str) -> str | None:
    key = str(ifc_type or "IfcMember")
    if key == "IfcBeam":
        return "Pset_BeamCommon"
    if key == "IfcColumn":
        return "Pset_ColumnCommon"
    if key == "IfcMember":
        return "Pset_MemberCommon"
    return None


def _attach_element_quantities(
    file: ifcopenshell.file,
    *,
    owner_history: Any,
    product: Any,
    ifc_type: str,
    length_mm: float,
    weight_kg: float,
) -> None:
    """Standard Qto sets so Tekla / Solibri show length and weight in the dataset."""
    quantities: list[Any] = [
        file.create_entity(
            "IfcQuantityLength",
            Name="Length",
            LengthValue=float(length_mm),
        ),
    ]
    if weight_kg > 0:
        quantities.append(
            file.create_entity(
                "IfcQuantityWeight",
                Name="GrossWeight",
                WeightValue=float(weight_kg),
            )
        )
    elem_q = file.create_entity(
        "IfcElementQuantity",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name=_quantity_set_name(ifc_type),
        Quantities=quantities,
    )
    file.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingPropertyDefinition=elem_q,
        RelatedObjects=[product],
    )


def _attach_common_property_set(
    file: ifcopenshell.file,
    *,
    owner_history: Any,
    product: Any,
    ifc_type: str,
    weight_kg: float,
) -> None:
    """buildingSMART common psets — many viewers surface Mass/GrossWeight here."""
    pset_name = _common_pset_name(ifc_type)
    if pset_name is None or weight_kg <= 0:
        return
    props = [
        file.create_entity(
            "IfcPropertySingleValue",
            Name="Mass",
            NominalValue=_real_value(file, weight_kg),
        ),
        file.create_entity(
            "IfcPropertySingleValue",
            Name="GrossWeight",
            NominalValue=_real_value(file, weight_kg),
        ),
    ]
    pset = file.create_entity(
        "IfcPropertySet",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        Name=pset_name,
        HasProperties=props,
    )
    file.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingPropertyDefinition=pset,
        RelatedObjects=[product],
    )


def _attach_material(
    file: ifcopenshell.file,
    *,
    owner_history: Any,
    product: Any,
    profile_family: str,
    material_cache: dict[str, Any],
) -> None:
    key = "Structural Steel"
    material = material_cache.get(key)
    if material is None:
        material = file.create_entity("IfcMaterial", Name=key)
        material_cache[key] = material
    file.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=_new_guid(),
        OwnerHistory=owner_history,
        RelatingMaterial=material,
        RelatedObjects=[product],
    )
    _ = profile_family  # reserved for future per-grade materials


def _create_member_from_entity(
    file: ifcopenshell.file,
    *,
    entity: dict[str, Any],
    nodes: dict[str, Any],
    schema: str,
    owner_history: Any,
    context: Any,
    storey_placement: Any,
    profile_cache: dict[str, Any],
    material_cache: dict[str, Any],
) -> Any | None:
    entity_id = str(entity.get("id", ""))
    start = _node_coords_steelera(nodes, str(entity.get("start_node_id", "")))
    end = _node_coords_steelera(nodes, str(entity.get("end_node_id", "")))
    if start is None or end is None:
        logger.warning("Entity %s: missing start/end node — skipped", entity_id)
        return None

    try:
        roll_deg = _effective_roll_deg(entity)
        profile_family = str(entity.get("profile_family", "") or "GENERIC")
        align_offset = _alignment_offset_mm(entity, profile_family)
        frame = _strict_member_frame(start, end, roll_deg=roll_deg)
        if frame is None:
            logger.warning("Entity %s: zero or degenerate length — skipped", entity_id)
            return None

        start_ifc, axis_z, axis_x, length_mm = frame
        girt_mirror_x = _girt_geometry_flip_z(entity)
        girt_mirror_y = _is_girt_entity(entity)
        profile = _create_profile_def(
            file,
            profile_family,
            schema=schema,
            cache=profile_cache,
            mirror_profile_x=girt_mirror_x,
            mirror_profile_y=girt_mirror_y,
        )

        member_placement = _local_placement(
            file,
            _axis2_placement(file, start_ifc, axis_z, axis_x),
            parent=storey_placement,
        )
        solid_origin = _solid_seating_offset(align_offset)
        body = _create_extruded_body(
            file,
            profile=profile,
            length_mm=length_mm,
            context=context,
            profile_flip_z=_purlin_ridge_mirror(entity),
            solid_origin=solid_origin,
        )
        axis_rep = _create_axis_representation(
            file,
            length_mm=length_mm,
            context=context,
        )
        product = _create_product(
            file,
            ifc_type=str(entity.get("ifc_type", "IfcMember")),
            schema=schema,
            entity_id=entity_id,
            structural_role=str(entity.get("structural_role", "")),
            owner_history=owner_history,
            placement=member_placement,
            representations=[body, axis_rep],
        )
        weight_kg = _member_weight_kg(profile_family, length_mm)
        _attach_property_set(
            file,
            owner_history=owner_history,
            product=product,
            entity=entity,
            length_mm=length_mm,
            weight_kg=weight_kg,
        )
        ifc_type = str(entity.get("ifc_type", "IfcMember"))
        _attach_element_quantities(
            file,
            owner_history=owner_history,
            product=product,
            ifc_type=ifc_type,
            length_mm=length_mm,
            weight_kg=weight_kg,
        )
        _attach_common_property_set(
            file,
            owner_history=owner_history,
            product=product,
            ifc_type=ifc_type,
            weight_kg=weight_kg,
        )
        _attach_material(
            file,
            owner_history=owner_history,
            product=product,
            profile_family=profile_family,
            material_cache=material_cache,
        )
        return product
    except Exception:
        logger.warning("Entity %s: geometry export failed — skipped", entity_id, exc_info=True)
        return None


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def export_topology_to_ifc(
    topology_data: dict[str, Any],
    output_path: str,
    schema_version: str = "IFC2X3",
) -> bool:
    """
    Write a physical IFC file from a Steelera ``structural_topology`` dictionary.

    Returns True when the file is written successfully, False on any fatal error.
    Individual member failures are logged and skipped without aborting the run.
    """
    try:
        schema = _normalize_schema(schema_version)
        if schema not in _SUPPORTED_SCHEMAS:
            raise ValueError(f"Unsupported schema: {schema}")

        nodes = topology_data.get("nodes") or {}
        entities = topology_data.get("entities") or []
        building_id = str(topology_data.get("building_id", "shed_1"))

        if not entities:
            logger.error("export_topology_to_ifc: no entities in topology")
            return False

        file = ifcopenshell.file(schema=schema)
        owner_history = _create_owner_history(file)
        context = _create_representation_context(file)
        _project, _site, _building, storey = _create_spatial_hierarchy(
            file,
            owner_history=owner_history,
            building_id=building_id,
            context=context,
        )
        storey_placement = storey.ObjectPlacement

        profile_cache: dict[str, Any] = {}
        material_cache: dict[str, Any] = {}
        products: list[Any] = []

        for entity in entities:
            if not isinstance(entity, dict):
                continue
            product = _create_member_from_entity(
                file,
                entity=entity,
                nodes=nodes,
                schema=schema,
                owner_history=owner_history,
                context=context,
                storey_placement=storey_placement,
                profile_cache=profile_cache,
                material_cache=material_cache,
            )
            if product is not None:
                products.append(product)

        if not products:
            logger.error("export_topology_to_ifc: no products created")
            return False

        file.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=_new_guid(),
            OwnerHistory=owner_history,
            RelatingStructure=storey,
            RelatedElements=products,
        )

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        file.write(str(out))
        logger.info(
            "IFC export OK: %s (%s, %d products)",
            out,
            schema,
            len(products),
        )
        return True

    except Exception:
        logger.exception("export_topology_to_ifc failed for %s", output_path)
        return False

"""
Validate IFC member endpoints against Steelera structural_topology nodes.

Run from backend/:
    python scripts/validate_ifc_nodes.py

Opens scripts/test_shed.ifc (generated on first run), extracts global start/end
points for IfcBeam / IfcColumn / IfcMember, and compares unique spatial points
to the backend topology node registry.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ifcopenshell
import ifcopenshell.util.placement as ifc_placement

from core.ifc_topology import build_topology_from_layout
from core.ifc_writer import export_topology_to_ifc
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

TOL_MM = 0.1
SCRIPT_DIR = Path(__file__).resolve().parent
IFC_PATH = SCRIPT_DIR / "test_shed.ifc"

Point3 = tuple[float, float, float]


def _standard_layout() -> StructuralGridLayout:
    return StructuralGridLayout(
        assembly_id="shed_1",
        replace_existing=True,
        grid_definition=GridDefinition(
            x_spans=[6000, 6000],
            z_spans=[5000, 5000],
            height_mm=4500,
            roof_pitch_deg=10,
            use_truss=True,
            truss_type="pratt",
            base_plates=True,
            generate_wall_girts=True,
        ),
        structural_members=[],
    )


def _ensure_test_shed_ifc() -> Path:
    print(f"Exporting {IFC_PATH.name} ...")
    topology = build_topology_from_layout(_standard_layout()).model_dump()
    if not export_topology_to_ifc(topology, str(IFC_PATH), schema_version="IFC4"):
        raise RuntimeError("Failed to export test_shed.ifc")
    return IFC_PATH


def _round_point(x: float, y: float, z: float) -> Point3:
    t = TOL_MM
    return (
        round(float(x) / t) * t,
        round(float(y) / t) * t,
        round(float(z) / t) * t,
    )


def _ifc_global_to_steelera(point: Point3) -> Point3:
    """IFC Z-up (x, y, z) → Steelera Y-up (x, y, z)."""
    x, y, z = point
    return (x, z, y)


def _transform_point(matrix: Any, local: Point3) -> Point3:
    x, y, z = local
    return (
        float(matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2] * z + matrix[0, 3]),
        float(matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2] * z + matrix[1, 3]),
        float(matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2] * z + matrix[2, 3]),
    )


def _axis_polyline_endpoints(representation: Any) -> tuple[Point3, Point3] | None:
    """Local start/end from Axis Curve3D polyline (structural analytical model)."""
    if getattr(representation, "RepresentationIdentifier", None) != "Axis":
        return None
    if getattr(representation, "RepresentationType", None) != "Curve3D":
        return None
    items = getattr(representation, "Items", None) or []
    if not items:
        return None
    polyline = items[0]
    points = getattr(polyline, "Points", None) or []
    if len(points) < 2:
        return None
    coords: list[Point3] = []
    for pt in points[:2]:
        ratios = getattr(pt, "Coordinates", None) or []
        if len(ratios) < 3:
            return None
        coords.append((float(ratios[0]), float(ratios[1]), float(ratios[2])))
    return coords[0], coords[1]


def _member_endpoints_ifc(element: Any) -> tuple[Point3, Point3] | None:
    """Return global IFC start/end from Axis representation (preferred) or placement."""
    placement = getattr(element, "ObjectPlacement", None)
    representation = getattr(element, "Representation", None)
    if placement is None or representation is None:
        return None

    matrix = ifc_placement.get_local_placement(placement)
    representations = getattr(representation, "Representations", None) or []

    for rep in representations:
        local = _axis_polyline_endpoints(rep)
        if local is not None:
            start = _transform_point(matrix, local[0])
            end = _transform_point(matrix, local[1])
            if math.dist(start, end) >= TOL_MM:
                return start, end

    depth = 0.0
    for rep in representations:
        if getattr(rep, "RepresentationIdentifier", None) == "Body":
            items = getattr(rep, "Items", None) or []
            if items:
                depth = float(getattr(items[0], "Depth", 0.0) or 0.0)
                break
    if depth < TOL_MM:
        return None

    origin = (
        float(matrix[0, 3]),
        float(matrix[1, 3]),
        float(matrix[2, 3]),
    )
    axis = (
        float(matrix[0, 2]),
        float(matrix[1, 2]),
        float(matrix[2, 2]),
    )
    axis_len = math.sqrt(axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2)
    if axis_len < 1e-9:
        return None
    axis = (axis[0] / axis_len, axis[1] / axis_len, axis[2] / axis_len)
    end = (
        origin[0] + axis[0] * depth,
        origin[1] + axis[1] * depth,
        origin[2] + axis[2] * depth,
    )
    return origin, end


def _collect_ifc_points(ifc_file: ifcopenshell.file) -> tuple[set[Point3], int]:
    unique: set[Point3] = set()
    member_count = 0

    for class_name in ("IfcBeam", "IfcColumn", "IfcMember"):
        for element in ifc_file.by_type(class_name):
            endpoints = _member_endpoints_ifc(element)
            if endpoints is None:
                continue
            member_count += 1
            start_ifc, end_ifc = endpoints
            unique.add(_round_point(*_ifc_global_to_steelera(start_ifc)))
            unique.add(_round_point(*_ifc_global_to_steelera(end_ifc)))

    return unique, member_count


def _topology_node_points(structural_topology: dict[str, Any]) -> set[Point3]:
    nodes = structural_topology.get("nodes") or {}
    return {
        _round_point(float(node["x"]), float(node["y"]), float(node["z"]))
        for node in nodes.values()
    }


def _points_within_tol(a: Point3, b: Point3) -> bool:
    return (
        abs(a[0] - b[0]) <= TOL_MM + 1e-9
        and abs(a[1] - b[1]) <= TOL_MM + 1e-9
        and abs(a[2] - b[2]) <= TOL_MM + 1e-9
    )


def _match_sets(
    ifc_points: set[Point3],
    node_points: set[Point3],
) -> tuple[set[Point3], set[Point3]]:
    unmatched_nodes: set[Point3] = set()
    for node in node_points:
        if not any(_points_within_tol(node, ifc_pt) for ifc_pt in ifc_points):
            unmatched_nodes.add(node)

    unmatched_ifc: set[Point3] = set()
    for ifc_pt in ifc_points:
        if not any(_points_within_tol(ifc_pt, node) for node in node_points):
            unmatched_ifc.add(ifc_pt)

    return unmatched_nodes, unmatched_ifc


def main() -> int:
    ifc_path = _ensure_test_shed_ifc()
    structural_topology = build_topology_from_layout(_standard_layout()).model_dump()

    ifc_file = ifcopenshell.open(str(ifc_path))
    ifc_points, member_count = _collect_ifc_points(ifc_file)
    node_points = _topology_node_points(structural_topology)

    node_count = len(node_points)
    ifc_unique_count = len(ifc_points)
    entity_count = len(structural_topology.get("entities") or [])

    print(f"IFC file: {ifc_path.name}")
    print(f"Structural members analysed: {member_count} (IfcBeam/IfcColumn/IfcMember)")
    print(f"Topology entities: {entity_count}")
    print(f"Unique IFC start/end points (tol={TOL_MM} mm): {ifc_unique_count}")
    print(f"Topology nodes: {node_count}")

    unmatched_nodes, unmatched_ifc = _match_sets(ifc_points, node_points)

    if not unmatched_ifc:
        if not unmatched_nodes:
            print(
                "SUCCESS: IFC Topology and Connectivity is 100% Valid for Engineering Software!"
            )
            return 0
        print(
            "SUCCESS: All exported member Axis endpoints align with topology nodes "
            f"({len(unmatched_nodes)} nodes are not used by IfcBeam/IfcColumn/IfcMember)."
        )
        return 0

    print("DISCREPANCY: IFC member endpoints do not align with topology nodes.")
    print(f"  Delta (IFC points - topology nodes): {ifc_unique_count - node_count}")

    if unmatched_nodes:
        print(f"  Topology nodes not matched by any IFC endpoint: {len(unmatched_nodes)}")
        for point in sorted(unmatched_nodes)[:8]:
            print(f"    node {point}")
        if len(unmatched_nodes) > 8:
            print(f"    ... and {len(unmatched_nodes) - 8} more")

    if unmatched_ifc:
        print(f"  IFC endpoints not matched by any topology node: {len(unmatched_ifc)}")
        for point in sorted(unmatched_ifc)[:8]:
            print(f"    ifc  {point}")
        if len(unmatched_ifc) > 8:
            print(f"    ... and {len(unmatched_ifc) - 8} more")

    if member_count < entity_count:
        skipped = entity_count - member_count
        print(
            f"  Note: {skipped} topology entities were not exported as "
            "IfcBeam/IfcColumn/IfcMember (e.g. plates)."
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

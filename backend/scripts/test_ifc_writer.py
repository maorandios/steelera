"""IFC writer smoke test. Run: python scripts/test_ifc_writer.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ifcopenshell
import ifcopenshell.util.placement as ifc_placement

from core.ifc_topology import build_topology_from_layout
from core.ifc_writer import export_topology_to_ifc
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

layout = StructuralGridLayout(
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

topology = build_topology_from_layout(layout)
data = topology.model_dump()

with tempfile.TemporaryDirectory() as tmp:
    path_23 = str(Path(tmp) / "shed_ifc2x3.ifc")
    path_4 = str(Path(tmp) / "shed_ifc4.ifc")

    assert export_topology_to_ifc(data, path_23, schema_version="IFC2X3") is True
    assert export_topology_to_ifc(data, path_4, schema_version="IFC4") is True

    f23 = ifcopenshell.open(path_23)
    f4 = ifcopenshell.open(path_4)

    products_23 = f23.by_type("IfcProduct")
    products_4 = f4.by_type("IfcProduct")
    assert len(products_23) >= 10
    assert len(products_4) >= 10

    beams = f4.by_type("IfcBeam")
    columns = f4.by_type("IfcColumn")
    assert len(beams) > 0
    assert len(columns) > 0

    psets = f4.by_type("IfcPropertySet")
    steelera_psets = [p for p in psets if p.Name == "Pset_SteeleraStructural"]
    assert len(steelera_psets) > 0

    sample_pset = steelera_psets[0]
    prop_names = {p.Name for p in sample_pset.HasProperties}
    assert "MemberWeightKg" in prop_names
    assert "MassPerMetreKg" in prop_names

    i_profiles_23 = f23.by_type("IfcIShapeProfileDef")
    arbitrary_23 = f23.by_type("IfcArbitraryClosedProfileDef")
    assert len(i_profiles_23) > 0
    assert len(arbitrary_23) > 0

    weights = f4.by_type("IfcQuantityWeight")
    assert len(weights) > 0

    beam_common = [p for p in f4.by_type("IfcPropertySet") if p.Name == "Pset_BeamCommon"]
    assert len(beam_common) > 0
    mass_props = {p.Name for p in beam_common[0].HasProperties}
    assert "Mass" in mass_props or "GrossWeight" in mass_props

    purlin_entity = next(e for e in data["entities"] if "purlin-0" in e["id"])
    assert purlin_entity.get("alignment") == "bottom"
    purlin = next(p for p in f4.by_type("IfcBeam") if "purlin-0" in p.Name)
    pl = purlin.ObjectPlacement.RelativePlacement
    ref = pl.RefDirection.DirectionRatios
    assert abs(ref[2]) > 0.05, "purlin roll should tilt RefDirection in the roof plane"

    purlin_right = next(e for e in data["entities"] if "purlin-6" in e["id"])
    assert purlin_right["rotation_euler"][0] < 0
    assert purlin_right["rotation_euler"][1] > 90
    assert abs(purlin_right["local_rotation"] - purlin_right["rotation_euler"][0]) < 1e-6

    col_entity = next(e for e in data["entities"] if e.get("ifc_type") == "IfcColumn")
    start_node = data["nodes"][col_entity["start_node_id"]]
    col = next(p for p in columns if p.Name == col_entity["id"])
    matrix = ifc_placement.get_local_placement(col.ObjectPlacement)
    origin_ifc = (float(matrix[0, 3]), float(matrix[1, 3]), float(matrix[2, 3]))
    origin_steelera = (origin_ifc[0], origin_ifc[2], origin_ifc[1])
    assert abs(origin_steelera[0] - start_node["x"]) < 0.1
    assert abs(origin_steelera[1] - start_node["y"]) < 0.1
    assert abs(origin_steelera[2] - start_node["z"]) < 0.1

    rep_ids = {
        r.RepresentationIdentifier
        for r in beams[0].Representation.Representations
    }
    assert "Body" in rep_ids
    assert "Axis" in rep_ids

    print(
        "PASS: ifc_writer",
        f"IFC2X3 products={len(products_23)}",
        f"IFC4 beams={len(beams)} columns={len(columns)}",
    )

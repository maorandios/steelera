"""Smoke test export router logic. Run: python scripts/test_export_endpoint.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ifcopenshell

from core.ifc_topology import build_topology_from_layout
from core.ifc_writer import export_topology_to_ifc
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

layout = StructuralGridLayout(
    assembly_id="shed_1",
    replace_existing=True,
    grid_definition=GridDefinition(
        x_spans=[6000],
        z_spans=[5000, 5000],
        height_mm=4000,
        roof_pitch_deg=10,
        use_truss=False,
    ),
    structural_members=[],
)

data = build_topology_from_layout(layout).model_dump()
out = Path(__file__).resolve().parent / "_test_export.ifc"
assert export_topology_to_ifc(data, str(out), schema_version="IFC4") is True
f = ifcopenshell.open(str(out))
assert len(f.by_type("IfcBeam")) > 0
out.unlink(missing_ok=True)
print("PASS: export endpoint data path")

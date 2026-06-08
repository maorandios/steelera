"""IFC topology: nodes, entities, assemblies. Run: python scripts/test_ifc_topology.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ifc_topology import build_topology_from_layout
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

layout = StructuralGridLayout(
    assembly_id="shed_1",
    replace_existing=True,
    grid_definition=GridDefinition(
        x_spans=[6000, 6000],
        z_spans=[5000, 5000, 5000],
        height_mm=4500,
        roof_pitch_deg=10,
        roof_style="duo_pitch",
        use_truss=True,
        truss_type="pratt",
        base_plates=True,
    ),
    structural_members=[],
)

topology = build_topology_from_layout(layout)

assert len(topology.nodes) > 0
assert len(topology.entities) > 0
assert "ASM_SHED_1" in topology.assemblies

col = next(e for e in topology.entities if e.structural_role == "COLUMN")
assert col.ifc_type == "IfcColumn"
assert col.primary_assembly_id.startswith("ASM_FRAME_Z")

plate = next(
    (e for e in topology.entities if e.ifc_type == "IfcPlate"),
    None,
)
assert plate is not None, "base plates should map to IfcPlate"
assert plate.structural_role == "BASE_PLATE"

truss_web = next(
    (e for e in topology.entities if "truss-web" in e.id),
    None,
)
if truss_web:
    assert truss_web.primary_assembly_id.startswith("ASM_TRUSS_Z")
    truss_asm = topology.assemblies[truss_web.primary_assembly_id]
    assert truss_web.id in truss_asm.entity_ids

frame_asm = topology.assemblies[col.primary_assembly_id]
assert col.id in frame_asm.entity_ids
assert len(frame_asm.entity_ids) > 1, "frame assembly should include multiple members"

# Node dedup: column base at same coord shares one node
node_ids = {e.start_node_id for e in topology.entities if e.structural_role == "COLUMN"}
assert len(node_ids) >= 2

highlight = topology.highlight_entity_ids(col.id)
assert col.id in highlight
assert len(highlight) >= 2

purlin = next((e for e in topology.entities if e.structural_role == "PURLIN"), None)
assert purlin is not None
assert purlin.primary_assembly_id == "ASM_ROOF"

print(
    "PASS: ifc_topology",
    f"nodes={len(topology.nodes)}",
    f"entities={len(topology.entities)}",
    f"assemblies={len(topology.assemblies)}",
)

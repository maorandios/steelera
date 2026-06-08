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
assert col.primary_assembly_id.startswith("ASM_PORTAL_Z")

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
assert truss_web is not None
assert truss_web.primary_assembly_id.startswith("ASM_TRUSS_Z")
assert "ASM_PORTAL" not in truss_web.assembly_ids
truss_asm = topology.assemblies[truss_web.primary_assembly_id]
assert truss_web.id in truss_asm.entity_ids
assert not any("col-" in eid for eid in truss_asm.entity_ids)

portal_asm = topology.assemblies[col.primary_assembly_id]
assert col.id in portal_asm.entity_ids
assert not any("truss-" in eid for eid in portal_asm.entity_ids), (
    "portal assembly must not include truss members"
)

highlight_col = topology.highlight_entity_ids(col.id)
assert col.id in highlight_col
assert not any("truss-" in eid for eid in highlight_col)

highlight_truss = topology.highlight_entity_ids(truss_web.id)
assert truss_web.id in highlight_truss
assert not any("col-" in eid for eid in highlight_truss)

purlin = next((e for e in topology.entities if e.structural_role == "PURLIN"), None)
assert purlin is not None
assert purlin.primary_assembly_id == "ASM_ROOF"
roof_asm = topology.assemblies["ASM_ROOF"]
assert len(roof_asm.entity_ids) > 1

# Rafter portal frame groups columns + rafters together.
layout_rafter = StructuralGridLayout(
    assembly_id="shed_1",
    replace_existing=True,
    grid_definition=GridDefinition(
        x_spans=[6000, 6000],
        z_spans=[5000, 5000, 5000],
        height_mm=4500,
        roof_pitch_deg=10,
        use_truss=False,
    ),
    structural_members=[],
)
topo_rafter = build_topology_from_layout(layout_rafter)
raf = next(e for e in topo_rafter.entities if e.structural_role == "RAFTER")
portal = topo_rafter.assemblies[raf.primary_assembly_id]
assert any(e.structural_role == "COLUMN" for e in topo_rafter.entities if e.id in portal.entity_ids)
assert raf.id in portal.entity_ids

print(
    "PASS: ifc_topology",
    f"nodes={len(topology.nodes)}",
    f"entities={len(topology.entities)}",
    f"assemblies={len(topology.assemblies)}",
)

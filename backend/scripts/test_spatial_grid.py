"""Universal spatial grid — grid engine + resolver. Run: python scripts/test_spatial_grid.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_member_catalog import members_from_shed_config
from core.member_resolver import layout_to_macro_members
from core.spatial_grid import StructuralGridEngine
from schemas.shed_assembly_config import (
    ShedAssemblyConfig,
    ShedBayConfiguration,
    ShedGlobalParameters,
    ShedGridLayout,
)
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralGridLayout, StructuralMember

# --- Grid engine ---
gd = GridDefinition(
    x_spans=[10000],
    z_spans=[5000, 5000],
    height_mm=4000,
    roof_pitch_deg=10,
    roof_style="duo_pitch",
)
grid = StructuralGridEngine.from_definition(gd)
assert grid.x_labels == ["A", "B"]
assert grid.z_labels == ["1", "2", "3"]
p = grid.resolve_node(GridNodeReference(x_axis="A", z_axis="1", elevation="ground"))
assert p == (0.0, 0.0, 0.0)
mid = grid.resolve_node(GridNodeReference(x_axis="A+1/2", z_axis="2", elevation="apex"))
assert 4000 < mid[1] < 6000
subs = grid.subdivide_x("A", "B", 4)
assert subs == ["A+1/4", "A+2/4", "A+3/4"]
print("PASS: grid engine")

# --- Resolver ---
layout = StructuralGridLayout(
    assembly_id="shed_1",
    replace_existing=True,
    grid_definition=gd,
    structural_members=[
        StructuralMember(
            id="col-A-1",
            element_type="column",
            profile="HEA200",
            start_node=GridNodeReference(x_axis="A", z_axis="1", elevation="ground"),
            end_node=GridNodeReference(x_axis="A", z_axis="1", elevation="eave"),
        ),
        StructuralMember(
            id="rafter-A-1",
            element_type="rafter",
            profile="IPE200",
            start_node=GridNodeReference(x_axis="A", z_axis="1", elevation="eave"),
            end_node=GridNodeReference(x_axis="A+1/2", z_axis="1", elevation="apex"),
        ),
    ],
)
macro = layout_to_macro_members(layout)
assert len(macro) == 2
print("PASS: member resolver", len(macro), "members")

# --- Catalog from legacy config ---
config = ShedAssemblyConfig(
    assembly_id="shed_1",
    replace_existing=True,
    global_parameters=ShedGlobalParameters(
        height_mm=4000, roof_pitch_deg=10, roof_style="duo_pitch"
    ),
    grid_layout=ShedGridLayout(x_spans=[10000], z_spans=[5000, 5000]),
    bays_configuration=[
        ShedBayConfiguration(
            bay_index=0,
            use_truss=True,
            truss_type="pratt",
            x_bracing_left_wall=True,
            x_bracing_right_wall=False,
            wall_girts=True,
            sag_rods=False,
        ),
        ShedBayConfiguration(
            bay_index=1,
            use_truss=False,
            truss_type="none",
            x_bracing_left_wall=False,
            x_bracing_right_wall=True,
            wall_girts=False,
            sag_rods=True,
        ),
    ],
    purlin_spacing_mm=1200,
    girt_spacing_mm=1500,
    generate_tie_beams=True,
)
members = members_from_shed_config(config)
full = layout_to_macro_members(
    StructuralGridLayout(
        assembly_id="shed_1",
        replace_existing=True,
        grid_definition=gd,
        structural_members=members,
    )
)
print("PASS: catalog resolver", len(full), "members")

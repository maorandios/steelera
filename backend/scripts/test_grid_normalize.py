import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_normalize import normalize_axis_ref, normalize_elevation
from core.spatial_grid import StructuralGridEngine
from schemas.spatial_grid import GridDefinition, GridNodeReference

assert normalize_elevation("rooftop") == "roof"
assert normalize_elevation("Ridge") == "ridge"
assert normalize_elevation("eave+1/2") == "eave+1/2"

grid = StructuralGridEngine.from_definition(
    GridDefinition(
        x_spans=[10000],
        z_spans=[5000],
        height_mm=4000,
        roof_pitch_deg=10,
        roof_style="duo_pitch",
    )
)
p = grid.resolve_node(
    GridNodeReference(x_axis="A", z_axis="1", elevation="rooftop")
)
assert p[1] >= 4000
mid = grid.resolve_x_mm("B-1/3")
assert 0 < mid < 10000
# Last X line: B+1/5 = 1/5 along span from A → B (10 m → 2000 mm)
wide = StructuralGridEngine.from_definition(
    GridDefinition(
        x_spans=[10000],
        z_spans=[5000],
        height_mm=4000,
        roof_pitch_deg=10,
        roof_style="duo_pitch",
    )
)
b15 = wide.resolve_x_mm("B+1/5")
assert abs(b15 - 2000) < 1.0
long = StructuralGridEngine.from_definition(
    GridDefinition(
        x_spans=[10000],
        z_spans=[5000, 5000, 5000, 5000, 5000, 5000],
        height_mm=4000,
        roof_pitch_deg=10,
        roof_style="duo_pitch",
    )
)
z_5_half = long.resolve_z_mm("5+1/2")
assert abs(z_5_half - 22500) < 1.0
z_end = long.resolve_z_mm("7+1/2")
assert abs(z_end - 27500) < 1.0
print("PASS: grid_normalize")

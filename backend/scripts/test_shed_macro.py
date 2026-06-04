"""Test portal-frame shed macro (no OpenAI). Run: python scripts/test_shed_macro.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geometry_engine import (
    cumulative_positions_from_spans,
    generate_shed_macro,
    macro_members_to_project_elements,
)

X_SPANS = [3000, 7000, 10000, 5000]
Z_SPANS = [5000, 5000, 5000, 5000, 5000, 5000]

members = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=X_SPANS,
    z_spans=Z_SPANS,
    height=4000,
    roof_pitch_deg=10,
    purlin_spacing=1200,
)

elements = macro_members_to_project_elements(members)

cols = [m for m in members if m["id"].startswith("shed-col-")]
rafs = [m for m in members if m["id"].startswith("shed-raf-")]
purlins = [m for m in members if m["id"].startswith("shed-purl-")]

x_positions = cumulative_positions_from_spans(X_SPANS)
z_positions = cumulative_positions_from_spans(Z_SPANS)
assert len(cols) == len(z_positions) * len(x_positions)

xs = sorted({m["position"][0] for m in cols})
zs = sorted({m["position"][2] for m in cols})
assert xs == x_positions, xs
assert zs == z_positions, zs

interior = next(m for m in cols if m["id"] == "shed-col-0-1")
outer = next(m for m in cols if m["id"] == "shed-col-0-0")
assert outer["length"] == 4000.0
assert interior["length"] > 4000.0

legacy = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[12000],
    z_spans=[6000, 6000, 6000, 6000],
    height=4000,
    roof_pitch_deg=10,
    purlin_spacing=1200,
)
legacy_cols = [m for m in legacy if m["id"].startswith("shed-col-")]
assert len(legacy_cols) == 5 * 2

print("PASS: shed macro (spans-driven)")
print(f"  columns={len(cols)} rafters={len(rafs)} purlins={len(purlins)}")
print(f"  X lines at {xs}")
print(f"  Z frames at {zs}")

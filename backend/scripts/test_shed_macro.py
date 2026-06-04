"""Test portal-frame shed macro (no OpenAI). Run: python scripts/test_shed_macro.py"""

import math
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


def _by_type(members: list[dict], element_type: str) -> list[dict]:
    return [m for m in members if m.get("element_type") == element_type]


members = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=X_SPANS,
    z_spans=Z_SPANS,
    height=4000,
    roof_pitch_deg=10,
    purlin_spacing=1200,
)

elements = macro_members_to_project_elements(members)

cols = _by_type(members, "column")
rafs = _by_type(members, "rafter")
purlins = _by_type(members, "purlin")
girts = _by_type(members, "wall_girt")

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

assert all(m.get("assembly_id") == "shed_1" for m in members)
assert all(e.assembly_id == "shed_1" for e in elements)
assert elements[0].element_type == "column"

legacy = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[12000],
    z_spans=[6000, 6000, 6000, 6000],
    height=4000,
    roof_pitch_deg=10,
    purlin_spacing=1200,
)
assert len(_by_type(legacy, "column")) == 5 * 2

# Mono pitch: ridge at X = width, single rafter per frame
mono = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[10000],
    z_spans=[5000],
    height=4000,
    roof_pitch_deg=10,
    roof_style="mono_pitch",
    generate_wall_girts=False,
    generate_tie_beams=False,
)
assert len(_by_type(mono, "rafter")) == 2  # frames at Z=0 and Z=5000
ridge_col = next(m for m in _by_type(mono, "column") if m["position"][0] == 10000.0)
assert ridge_col["length"] > 4000.0

# Flat roof: zero pitch, one rafter per frame
flat = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[8000],
    z_spans=[5000],
    height=3500,
    roof_pitch_deg=10,
    roof_style="flat",
    generate_wall_girts=False,
)
flat_rafs = _by_type(flat, "rafter")
assert len(flat_rafs) == 2
assert all(r["rotation"] == [0.0, 0.0, 0.0] for r in flat_rafs)

# Truss mode
trussed = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[8000],
    z_spans=[5000, 5000],
    height=4000,
    use_truss=True,
    generate_wall_girts=False,
    generate_tie_beams=False,
)
assert len(_by_type(trussed, "rafter")) == 0
assert len(_by_type(trussed, "truss_chord")) >= 4
assert len(_by_type(trussed, "truss_web")) >= 4

# Bracing + sag rods
full = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=X_SPANS,
    z_spans=Z_SPANS,
    height=4000,
    use_bracing=True,
    use_sag_rods=True,
)
braces = _by_type(full, "bracing")
sags = _by_type(full, "sag_rod")
assert len(braces) > 0
assert len(sags) > 0

# Wall braces on side walls (X=0 / X=width), column base to top in end Z bays.
wall_braces = [b for b in braces if b["id"].startswith("shed-brace-wall")]
for b in wall_braces:
    nodes = b["nodes"]
    assert nodes["start"][1] == 0.0 or nodes["end"][1] == 0.0
    x = nodes["start"][0]
    assert x == 0.0 or x == 25000.0

# Sag rods at Z bay mid-span (5000), not on portal frame line 0.
z_frames = cumulative_positions_from_spans(Z_SPANS)
z_mid_first_bay = (z_frames[0] + z_frames[1]) / 2
for s in sags:
    z0, z1 = s["nodes"]["start"][2], s["nodes"]["end"][2]
    assert z0 == z1
    assert any(
        abs((z_frames[i] + z_frames[i + 1]) / 2 - z0) < 1.0
        for i in range(len(z_frames) - 1)
    )
assert len(sags) < 40, f"too many sag rods ({len(sags)}), roof mesh would clutter viewport"

trussed_duo = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[10000],
    z_spans=[5000],
    height=4000,
    roof_pitch_deg=10,
    use_truss=True,
)
left = [m for m in trussed_duo if "shed-truss" in m["id"] and "-L-" in m["id"]]
right = [m for m in trussed_duo if "shed-truss" in m["id"] and "-R-" in m["id"]]
assert len(left) > 0 and len(right) > 0
assert len(_by_type(full, "tie_beam")) > 0
assert len(girts) > 0

zero_pitch_duo = generate_shed_macro(
    assembly_id="shed_1",
    x_spans=[8000],
    z_spans=[5000],
    height=4000,
    roof_pitch_deg=0,
    roof_style="duo_pitch",
)
for m in zero_pitch_duo:
    for key in ("position", "rotation"):
        for v in m[key]:
            assert math.isfinite(v), (m["id"], key, v)
    if m.get("nodes"):
        for pt in m["nodes"].values():
            for v in pt:
                assert math.isfinite(v), (m["id"], pt)
    assert m["length"] >= 1.0

print("PASS: shed macro (industrial)")
print(
    f"  columns={len(cols)} rafters={len(rafs)} purlins={len(purlins)} "
    f"girts={len(girts)}"
)
print(f"  X lines at {xs}")
print(f"  Z frames at {zs}")

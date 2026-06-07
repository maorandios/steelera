"""Truss web-pattern registry coverage. Run: python scripts/test_truss_types.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_member_catalog import members_from_grid_definition
from core.member_resolver import layout_to_macro_members
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

DUO_TYPES = ["pratt", "howe", "warren", "fink", "king_post", "queen_post", "scissor"]


def _build(style: str, pitch: float, truss_type: str) -> tuple[list, list[dict]]:
    gd = GridDefinition(
        x_spans=[12000],
        z_spans=[5000, 5000, 5000],
        height_mm=4000,
        roof_pitch_deg=pitch,
        roof_style=style,
        use_truss=True,
        truss_type=truss_type,
    )
    members = members_from_grid_definition(gd)
    layout = StructuralGridLayout(grid_definition=gd, structural_members=members)
    macro = layout_to_macro_members(layout)
    return members, macro


def _resolved_webs(macro: list[dict]) -> list[dict]:
    return [m for m in macro if "truss-web" in str(m.get("id", ""))]


def _finite(macro: list[dict]) -> bool:
    for m in macro:
        nodes = m.get("nodes") or {}
        for pt in nodes.values():
            if not all(isinstance(v, (int, float)) and v == v for v in pt):
                return False
    return True


# Every duo-pitch truss type must produce chords + at least one resolved web,
# with finite geometry and no degenerate (zero-length) leftovers.
for t in DUO_TYPES:
    members, macro = _build("duo_pitch", 15.0, t)
    chords = [m for m in members if m.element_type == "truss_chord"]
    rweb = _resolved_webs(macro)
    assert len(chords) >= 3, (t, len(chords))
    assert len(rweb) > 0, (t, "no resolved webs")
    assert _finite(macro), (t, "non-finite geometry")
    # No truss member should be shorter than 1 mm after resolution.
    for m in macro:
        if "truss" in str(m.get("id", "")):
            assert m["length"] >= 1.0, (t, m["id"], m["length"])

# Scissor adds an extra (kinked) bottom chord vs a flat-tie truss.
fink_chords = [m for m in _build("duo_pitch", 15.0, "fink")[0] if m.element_type == "truss_chord"]
scissor_chords = [m for m in _build("duo_pitch", 15.0, "scissor")[0] if m.element_type == "truss_chord"]
assert len(scissor_chords) > len(fink_chords), (len(scissor_chords), len(fink_chords))

# Apex-only patterns gracefully fall back to Pratt on mono/flat roofs.
for style, pitch in (("mono_pitch", 12.0), ("flat", 0.0)):
    for t in ("fink", "scissor", "pratt", "warren"):
        members, macro = _build(style, pitch, t)
        assert len(_resolved_webs(macro)) > 0, (style, t)
        assert _finite(macro), (style, t)

# Normalization: aliases + suffixes resolve to canonical types.
gd = GridDefinition(
    x_spans=[10000], z_spans=[5000], height_mm=4000, roof_pitch_deg=10,
    use_truss=True, truss_type="Howe Truss",
)
assert gd.truss_type == "howe", gd.truss_type
gd = GridDefinition(
    x_spans=[10000], z_spans=[5000], height_mm=4000, roof_pitch_deg=10,
    use_truss=True, truss_type="kingpost",
)
assert gd.truss_type == "king_post", gd.truss_type

# Scissor: bottom-chord ties follow the raised bottom chord (not eave level).
_, macro = _build("duo_pitch", 18.0, "scissor")
gd_scissor = GridDefinition(
    x_spans=[14000],
    z_spans=[5000, 5000, 5000],
    height_mm=5000,
    roof_pitch_deg=18,
    roof_style="duo_pitch",
    use_truss=True,
    truss_type="scissor",
    bottom_chord_restraint=True,
    roof_bracing=True,
)
members = members_from_grid_definition(gd_scissor)
layout = StructuralGridLayout(grid_definition=gd_scissor, structural_members=members)
macro = layout_to_macro_members(layout)
bcties = [m for m in macro if "bctie" in str(m.get("id", ""))]
assert bcties, "no bottom-chord restraint ties"
for m in bcties:
    y = m["nodes"]["start"][1]
    assert y > 5200.0, (m["id"], y)
roof_braces = [m for m in macro if "brace-roof-s" in str(m.get("id", ""))]
assert len(roof_braces) == 0, ("truss end bays should not get rafter-style roof X", len(roof_braces))

# Scissor shed: no fly braces / gable X-bracing on truss frames; girts bay-sized.
gd_scissor_full = GridDefinition(
    x_spans=[12000],
    z_spans=[5000, 5000, 5000],
    height_mm=5000,
    roof_pitch_deg=18,
    roof_style="duo_pitch",
    use_truss=True,
    truss_type="scissor",
    generate_wall_girts=True,
    fly_braces=True,
    gable_bracing=True,
    roof_bracing=True,
)
macro_full = layout_to_macro_members(
    StructuralGridLayout(
        grid_definition=gd_scissor_full,
        structural_members=members_from_grid_definition(gd_scissor_full),
    )
)
assert not [m for m in macro_full if m.get("element_type") == "fly_brace"], "fly braces on truss frames"
assert not [m for m in macro_full if m.get("id", "").endswith("end-1-a")], "gable X on truss"
assert not [m for m in macro_full if "-brace-A-" in m.get("id", "")], "side-wall X on truss bays"
assert not [m for m in macro_full if "brace-roof-s" in m.get("id", "")], "roof X on truss bays"
gable_girts = [m for m in macro_full if "gablegirt" in str(m.get("id", ""))]
assert gable_girts, "no gable girts"
assert all(abs(m["nodes"]["start"][0] - m["nodes"]["end"][0]) < 7000 for m in gable_girts), (
    "full-width gable girt",
    max(abs(m["nodes"]["start"][0] - m["nodes"]["end"][0]) for m in gable_girts),
)

# Stale AI/hand members with bracing must not survive truss catalog resolution.
from core.grid_layout_utils import ensure_layout_members
from schemas.spatial_grid import GridNodeReference, StructuralMember

stale = StructuralMember(
    id="shed_1-brace-roof-s0-b0-a",
    element_type="bracing",
    profile="L50x50",
    start_node=GridNodeReference(x_axis="A", z_axis="1", elevation="eave"),
    end_node=GridNodeReference(x_axis="A+1/4", z_axis="2", elevation="roof"),
)
layout_stale = StructuralGridLayout(
    grid_definition=gd_scissor_full,
    structural_members=[stale],
)
fresh = ensure_layout_members(layout_stale)
assert not any(m.element_type == "bracing" for m in fresh.structural_members), "stale truss bracing"

# Mono-pitch truss: gable ends = single-panel trapezoid; interior = panelled webs.
import math

gd_mono_truss = GridDefinition(
    x_spans=[12000],
    z_spans=[5000, 5000, 5000],
    height_mm=4000,
    roof_pitch_deg=10,
    roof_style="mono_pitch",
    mono_high_side="B",
    use_truss=True,
    truss_type="pratt",
    generate_wall_girts=True,
)
mono_members = members_from_grid_definition(gd_mono_truss)
mono_macro = layout_to_macro_members(
    StructuralGridLayout(
        grid_definition=gd_mono_truss,
        structural_members=mono_members,
    )
)
# Gable end: one BC + one TC + panel webs (trapezoid, not triangle fan).
gable_tc = [m for m in mono_members if m.id == "shed_1-truss-tc-1-0"]
assert len(gable_tc) == 1, "gable end needs single top chord"
assert not any(m.id == "shed_1-truss-tc-1-1" for m in mono_members), "gable end over-panelled"
gable_webs = [m for m in mono_macro if m["id"].startswith("shed_1-truss-web-1-")]
assert 2 <= len(gable_webs) <= 3, len(gable_webs)
assert any(
    m["nodes"]["start"][1] < 4100 and m["nodes"]["end"][1] > 5000
    for m in gable_webs
), "gable trapezoid missing high-side vertical or diagonal"
# Interior frame: multi-panel filaments.
interior_webs = [m for m in mono_macro if m["id"].startswith("shed_1-truss-web-2-")]
assert len(interior_webs) >= 5, len(interior_webs)
high_gable_col = next(m for m in mono_macro if m["id"] == "shed_1-col-B-1")
assert abs(high_gable_col["length"] - 4000.0) < 2.0, high_gable_col["length"]

print("PASS: truss types")
print(f"  duo types verified: {', '.join(DUO_TYPES)}")

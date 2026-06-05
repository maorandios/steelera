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

print("PASS: truss types")
print(f"  duo types verified: {', '.join(DUO_TYPES)}")

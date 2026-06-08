"""Truss chord/web profile overrides. Run: python scripts/test_truss_profiles.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_member_catalog import members_from_grid_definition
from core.profile_overrides import (
    apply_profile_overrides_to_layout,
    extract_profiles_from_text,
)
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

USER_SNIPPET = (
    "Truss Chords (TC & BC): SHS120x120x6 - Truss Web Diagonals: L60x60x6"
)

parsed = extract_profiles_from_text(USER_SNIPPET)
assert parsed.get("truss_chord_profile") == "SHS120x120x6", parsed
assert parsed.get("truss_web_profile") == "L60x60x6", parsed

gd = GridDefinition(
    x_spans=[18000],
    z_spans=[6000, 6000],
    height_mm=7500,
    roof_pitch_deg=10,
    use_truss=True,
    truss_type="pratt",
    generate_purlins=False,
    generate_wall_girts=False,
    truss_chord_profile="SHS120x120x6",
    truss_web_profile="L60x60x6",
)
members = members_from_grid_definition(gd)
chord_profiles = {m.profile for m in members if m.element_type == "truss_chord"}
web_profiles = {m.profile for m in members if m.element_type == "truss_web"}
assert chord_profiles == {"SHS120x120x6"}, chord_profiles
assert web_profiles == {"L60x60x6"}, web_profiles
assert "IPE200" not in chord_profiles
assert "L50x50" not in web_profiles

layout = StructuralGridLayout(
    assembly_id="shed_1",
    replace_existing=True,
    grid_definition=GridDefinition(
        x_spans=[12000],
        z_spans=[5000, 5000],
        height_mm=5000,
        roof_pitch_deg=12,
        use_truss=True,
        truss_type="pratt",
    ),
    structural_members=[],
)
refreshed = apply_profile_overrides_to_layout(layout, user_text=USER_SNIPPET)
assert refreshed.grid_definition.truss_chord_profile == "SHS120x120x6"
assert refreshed.grid_definition.truss_web_profile == "L60x60x6"
refreshed_chords = {
    m.profile for m in refreshed.structural_members if m.element_type == "truss_chord"
}
refreshed_webs = {
    m.profile for m in refreshed.structural_members if m.element_type == "truss_web"
}
assert refreshed_chords == {"SHS120x120x6"}, refreshed_chords
assert refreshed_webs == {"L60x60x6"}, refreshed_webs

print("PASS: test_truss_profiles")

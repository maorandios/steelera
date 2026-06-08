"""Grid intent + catalog flag tests. Run: python scripts/test_grid_intent.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_intent import extract_grid_intent_from_text, merge_grid_intent_into_definition
from core.grid_member_catalog import members_from_grid_definition
from schemas.spatial_grid import GridDefinition

USER_SPEC_SNIPPET = """
Roof Purlins: DISABLED (0 / Do not generate any longitudinal roof purlins)
Wall Girts: DISABLED (0 / Do not generate any longitudinal wall girts)
Roof Cross-Bracing: ENABLED
Wall Cross-Bracing: ENABLED
Truss Type: PRATT Truss
"""

intent = extract_grid_intent_from_text(USER_SPEC_SNIPPET)
assert intent.get("generate_purlins") is False, intent
assert intent.get("generate_wall_girts") is False, intent
assert intent.get("roof_bracing") is True, intent
assert intent.get("x_bracing") is True, intent
assert intent.get("use_truss") is True, intent

# AI tool args must win over regex for booleans.
ai_grid = GridDefinition(
    x_spans=[18000],
    z_spans=[6000] * 6,
    height_mm=7500,
    roof_pitch_deg=10,
    use_truss=True,
    truss_type="pratt",
    x_bracing=True,
    roof_bracing=True,
    generate_purlins=False,
    generate_wall_girts=False,
)
merged = merge_grid_intent_into_definition(ai_grid, intent, fill_gaps_only=True)
assert merged.generate_purlins is False
assert merged.generate_wall_girts is False
assert merged.x_bracing is True
assert merged.roof_bracing is True

members = members_from_grid_definition(merged, assembly_id="shed_1")
types = {m.element_type for m in members}
assert "purlin" not in types, types
assert "wall_girt" not in types, types
assert "bracing" in types or "x_brace" in types, types

# Truss shed with bracing enabled must emit roof/wall X members.
bracing = [m for m in members if m.element_type in ("bracing", "x_brace")]
assert len(bracing) > 0, f"expected bracing, got types={sorted(types)}"

print("PASS: test_grid_intent")

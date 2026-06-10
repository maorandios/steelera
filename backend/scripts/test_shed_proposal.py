"""Shed proposal engine tests. Run: python scripts/test_shed_proposal.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.shed_proposal import propose_shed_configuration
from schemas.proposal import ShedProposalRequest

req = ShedProposalRequest(
    use_case="Industrial warehouse",
    width_mm=18_000,
    length_mm=42_000,
    height_mm=7_500,
    roof_style="duo_pitch",
    exposure="open",
    bay_spacing_mm=6_000,
)
resp = propose_shed_configuration(req)
gd = resp.grid_definition

assert gd.use_truss is True
assert gd.truss_type == "pratt"
assert len(gd.z_spans) == 7
assert abs(sum(gd.z_spans) - 42_000) < 1.0
assert gd.x_bracing is True
assert gd.roof_bracing is True
assert gd.column_profile
assert gd.truss_chord_profile.startswith("SHS")
assert gd.truss_web_profile
assert gd.tie_beam_profile and gd.tie_beam_profile.startswith("IPE")
assert len(resp.rationale) >= 4

small = propose_shed_configuration(
    ShedProposalRequest(
        width_mm=12_000,
        length_mm=24_000,
        height_mm=4_500,
        exposure="sheltered",
    )
)
assert small.grid_definition.use_truss is False
assert small.grid_definition.truss_type == "none"

print("PASS: test_shed_proposal")

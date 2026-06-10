"""Proposal copy / disclaimer tests. Run: python scripts/test_proposal_copy.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.proposal_copy import PROPOSAL_DISCLAIMER, build_proposal_rationale
from schemas.site import StructuralRecommendations

rec = StructuralRecommendations(
    bay_spacing_mm=6_250,
    use_truss=True,
    truss_type="pratt",
    column_profile="HEA300",
    truss_chord_profile="SHS150x150x8",
    truss_web_profile="L70x70x6",
    x_bracing=True,
    roof_bracing=True,
    gable_bracing=True,
    sag_rods=True,
    fly_braces=False,
    haunches=False,
)

rationale = build_proposal_rationale(
    site_location="Tel Aviv, Israel",
    mean_wind_ms=2.8,
    exposure_proxy_ms=5.0,
    terrain_label="urban (Cat IV)",
    load_index=4.7,
    effective_load_index=8.5,
    rec=rec,
    bay_mm=6_250,
    n_frames=9,
    width_m=18.0,
    length_m=50.0,
    height_m=8.0,
    use_case="Industrial warehouse",
    prelim_roof_kn_m2=1.07,
    prelim_column_m_knm=12.0,
    prelim_chord_n_kn=73.0,
)

text = "\n".join(rationale)
assert "Code wind speed was not calculated" in text
assert "exposure proxy" in text
assert "design proxy" not in text.lower()
assert "EC3 screening" not in text
assert "EC3-style" in text
assert "not a full structural verification" in text
assert "Suggested configuration" in text
assert "Suggested starting sections" in text
assert "Conservative sizing floor" in text
assert PROPOSAL_DISCLAIMER in text
assert "licensed structural engineer" in text

print("PASS: test_proposal_copy")

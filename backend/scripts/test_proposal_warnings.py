"""Proposal warning tests. Run: python scripts/test_proposal_warnings.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.preliminary_loads import PreliminaryLoads, estimate_preliminary_loads
from core.proposal_warnings import (
    CHORD_UTIL_MEANINGFUL_MIN,
    COLUMN_UTIL_MEANINGFUL_MIN,
    MINIMUM_RULES_SUMMARY,
    TIE_UTIL_MEANINGFUL_MIN,
    build_proposal_warnings,
    chord_utilization_warnings,
    column_utilization_warnings,
    minimum_rules_summary_warning,
    tie_utilization_warnings,
)
from core.shed_proposal import propose_shed_configuration
from schemas.proposal import SectionTierPackage, ShedProposalRequest
from schemas.site import SiteContext

loads = PreliminaryLoads(
    effective_load_index=8.5,
    roof_pressure_kn_m2=0.9,
    frame_line_load_kn_m=5.0,
    column_axial_kn=80.0,
    column_moment_knm=200.0,
    rafter_moment_knm=150.0,
    chord_axial_kn=60.0,
    truss_depth_mm=2000.0,
    web_axial_kn=80.0,
    web_length_mm=3000.0,
    tie_beam_axial_kn=50.0,
    tie_beam_length_mm=40000.0,
    bracing_axial_kn=35.0,
    bracing_length_mm=12000.0,
)

farm_warnings = build_proposal_warnings(
    height_mm=19_000,
    length_mm=50_000,
    width_mm=24_000,
    is_open=True,
    loads=loads,
    use_case="Farm building",
)
assert any("farm building" in w.lower() or "farm" in w.lower() for w in farm_warnings)
assert any("19" in w for w in farm_warnings)

low_chord_tiers = [
    SectionTierPackage(
        tier="recommended",
        column_profile="HEA400",
        column_utilization=0.7,
        truss_chord_profile="SHS200x200x10",
        chord_utilization=0.05,
        bracing_profile="L60x60x6",
    ),
]
chord_warns = chord_utilization_warnings(low_chord_tiers, use_truss=True)
assert len(chord_warns) == 1
assert "unusually low" in chord_warns[0].lower()
assert 0.05 < CHORD_UTIL_MEANINGFUL_MIN

mixed_tiers = [
    SectionTierPackage(
        tier="light",
        column_profile="HEA400",
        truss_chord_profile="SHS200x200x8",
        chord_utilization=0.05,
        bracing_profile="L50x50",
    ),
    SectionTierPackage(
        tier="recommended",
        column_profile="HEA450",
        truss_chord_profile="SHS200x200x10",
        chord_utilization=0.25,
        bracing_profile="L60x60x6",
    ),
]
mixed_warns = chord_utilization_warnings(mixed_tiers, use_truss=True)
assert any("some chord" in w.lower() for w in mixed_warns)

low_col_tiers = [
    SectionTierPackage(
        tier="light",
        column_profile="HEB320",
        column_utilization=0.32,
        bracing_profile="L60x60x6",
    ),
    SectionTierPackage(
        tier="recommended",
        column_profile="HEB340",
        column_utilization=0.28,
        bracing_profile="L60x60x6",
    ),
    SectionTierPackage(
        tier="conservative",
        column_profile="HEB360",
        column_utilization=0.26,
        bracing_profile="L70x70x6",
    ),
]
col_warns = column_utilization_warnings(
    low_col_tiers, height_mm=10_000, roof_style="mono_pitch"
)
assert len(col_warns) == 1
assert "low utilization" in col_warns[0].lower()
assert 0.28 < COLUMN_UTIL_MEANINGFUL_MIN

mono_warns = build_proposal_warnings(
    height_mm=10_000,
    length_mm=50_000,
    width_mm=24_000,
    is_open=False,
    loads=loads,
    roof_style="mono_pitch",
)
assert any("mono-pitch" in w.lower() for w in mono_warns)

low_tie_tiers = [
    SectionTierPackage(
        tier="recommended",
        column_profile="HEA400",
        column_utilization=0.5,
        tie_beam_profile="IPE270",
        tie_beam_utilization=0.05,
        bracing_profile="L60x60x6",
    ),
]
tie_warns = tie_utilization_warnings(low_tie_tiers)
assert len(tie_warns) == 1
assert 0.05 < TIE_UTIL_MEANINGFUL_MIN

summary_tiers = [
    SectionTierPackage(
        tier="light",
        column_profile="HEB320",
        column_utilization=0.32,
        truss_chord_profile="SHS200x200x10",
        chord_utilization=0.05,
        tie_beam_profile="IPE240",
        tie_beam_utilization=0.04,
        bracing_profile="L60x60x6",
    ),
    SectionTierPackage(
        tier="recommended",
        column_profile="HEB340",
        column_utilization=0.28,
        truss_chord_profile="SHS200x200x10",
        chord_utilization=0.05,
        tie_beam_profile="IPE270",
        tie_beam_utilization=0.05,
        bracing_profile="L60x60x6",
    ),
]
summary_warns = minimum_rules_summary_warning(summary_tiers, use_truss=True)
assert summary_warns == [MINIMUM_RULES_SUMMARY]

site = SiteContext(
    latitude=32.0,
    longitude=34.8,
    location_label="Test",
    mean_wind_ms=5.0,
    design_wind_proxy_ms=7.0,
    terrain_class="II",
    exposure="open",
    load_index=8.0,
)
prelim = estimate_preliminary_loads(
    width_mm=24_000,
    length_mm=50_000,
    height_mm=7_500,
    roof_pitch_deg=10,
    bay_spacing_mm=6_000,
    effective_load_index=8.5,
    site=site,
)
resp = propose_shed_configuration(
    ShedProposalRequest(
        use_case="Farm building",
        width_mm=24_000,
        length_mm=50_000,
        height_mm=19_000,
        roof_style="duo_pitch",
        roof_pitch_deg=10,
        exposure="open",
    )
)
assert any("farm" in w.lower() for w in resp.warnings)
if resp.recommendations and resp.recommendations.use_truss:
    assert any("chord" in w.lower() for w in resp.warnings)

print("PASS: test_proposal_warnings")

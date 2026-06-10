"""Section tier package tests. Run: python scripts/test_proposal_tiers.py"""



import sys

from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



from core.load_engine import compute_section_tier_options

from core.section_props import section_properties

from core.shed_proposal import propose_shed_configuration

from schemas.proposal import ShedProposalRequest

from schemas.site import SiteContext



dubai_open = SiteContext(

    latitude=25.2,

    longitude=55.3,

    location_label="Dubai",

    mean_wind_ms=5.5,

    design_wind_proxy_ms=7.5,

    terrain_class="II",

    exposure="open",

    load_index=11.0,

)



opts = compute_section_tier_options(

    width_mm=24_000,

    length_mm=50_000,

    height_mm=12_000,

    roof_pitch_deg=10,

    site=dubai_open,

    bay_spacing_mm=6_000,

    use_truss=True,

)



light = opts["light"]

rec = opts["recommended"]

con = opts["conservative"]



assert light["column_profile"] != con["column_profile"] or light == con

assert rec["column_profile"]
assert rec["bracing_profile"]
assert rec.get("bracing_utilization") is not None
assert con.get("bracing_utilization") is not None

assert str(rec["truss_chord_profile"]).startswith("SHS")



resp = propose_shed_configuration(

    ShedProposalRequest(

        use_case="Warehouse",

        width_mm=24_000,

        length_mm=50_000,

        height_mm=12_000,

        roof_style="duo_pitch",

        roof_pitch_deg=10,

        latitude=25.2,

        longitude=55.3,

        location_label="Dubai",

        exposure="open",

    )

)



assert len(resp.section_tiers) == 3

assert resp.ai_review is not None

assert resp.active_tier in ("light", "recommended", "conservative")

assert resp.grid_definition.column_profile

assert resp.warnings

assert any("Large-height" in w or "Tall eave" in w for w in resp.warnings)


# 24×50×15 m open workshop — recommended util ~0.60–0.80 (not HEA600 @ 0.42).
tall_resp = propose_shed_configuration(
    ShedProposalRequest(
        use_case="Workshop",
        width_mm=24_000,
        length_mm=50_000,
        height_mm=15_000,
        roof_style="duo_pitch",
        roof_pitch_deg=10,
        latitude=25.2,
        longitude=55.3,
        location_label="Dubai",
        exposure="open",
    )
)
tall_rec = next(t for t in tall_resp.section_tiers if t.tier == "recommended")
tall_con = next(t for t in tall_resp.section_tiers if t.tier == "conservative")
assert tall_resp.active_tier == "recommended"
assert tall_rec.column_utilization is not None
assert 0.55 <= tall_rec.column_utilization <= 0.80
assert tall_rec.column_utilization > 0.42
assert tall_con.column_utilization is not None
assert tall_con.column_utilization < tall_rec.column_utilization
assert tall_resp.grid_definition.column_profile == tall_rec.column_profile

# High-exposure site pushes heavier recommended tier.
high_load_opts = compute_section_tier_options(
    width_mm=24_000,
    length_mm=50_000,
    height_mm=15_000,
    roof_pitch_deg=10,
    site=dubai_open,
    bay_spacing_mm=6_000,
    use_truss=True,
)
hl_rec = high_load_opts["recommended"]
assert hl_rec["column_profile"] in ("HEA500", "HEA550"), hl_rec
assert 0.60 <= float(hl_rec["column_utilization"]) <= 0.80

# Large trussed shed — chords, webs, and ties should spread across tiers.
large_opts = compute_section_tier_options(
    width_mm=28_000,
    length_mm=70_000,
    height_mm=19_000,
    roof_pitch_deg=10,
    site=dubai_open,
    bay_spacing_mm=6_000,
    use_truss=True,
)
assert large_opts["light"]["truss_chord_profile"] != large_opts["conservative"]["truss_chord_profile"]
assert large_opts["light"]["truss_web_profile"] != large_opts["conservative"]["truss_web_profile"]
assert large_opts["light"]["tie_beam_profile"] != large_opts["conservative"]["tie_beam_profile"]

# 24×100×21 m — tall/long bracing should reach L70+ recommended, L80+ conservative.
long_tall_opts = compute_section_tier_options(
    width_mm=24_000,
    length_mm=100_000,
    height_mm=21_000,
    roof_pitch_deg=10,
    site=dubai_open,
    bay_spacing_mm=6_000,
    use_truss=True,
)
lt_rec = long_tall_opts["recommended"]
lt_con = long_tall_opts["conservative"]
assert float(lt_rec["bracing_utilization"]) <= 0.90
assert float(lt_con["bracing_utilization"]) <= 0.90
rec_brace_mass = section_properties(str(lt_rec["bracing_profile"])).mass_kg_m
con_brace_mass = section_properties(str(lt_con["bracing_profile"])).mass_kg_m
l70_mass = section_properties("L70x70x6").mass_kg_m
l80_mass = section_properties("L80x80x8").mass_kg_m
assert rec_brace_mass >= l70_mass - 0.01, lt_rec
assert con_brace_mass >= l80_mass - 0.01, lt_con

# 24×50×10 urban-scale — bracing recommended at least L60, not thin CHS42.
urban = SiteContext(
    latitude=32.08,
    longitude=34.78,
    location_label="Urban",
    mean_wind_ms=4.5,
    design_wind_proxy_ms=6.0,
    terrain_class="IV",
    exposure="sheltered",
    load_index=6.5,
)
industrial_opts = compute_section_tier_options(
    width_mm=24_000,
    length_mm=50_000,
    height_mm=10_000,
    roof_pitch_deg=10,
    site=urban,
    bay_spacing_mm=6_000,
    use_truss=True,
    roof_style="mono_pitch",
)
ind_rec = industrial_opts["recommended"]
assert str(ind_rec["bracing_profile"]).startswith("L"), ind_rec
l60_mass = section_properties("L60x60x6").mass_kg_m
assert section_properties(str(ind_rec["bracing_profile"])).mass_kg_m >= l60_mass - 0.01

mono_resp = propose_shed_configuration(
    ShedProposalRequest(
        use_case="Warehouse",
        width_mm=24_000,
        length_mm=50_000,
        height_mm=10_000,
        roof_style="mono_pitch",
        roof_pitch_deg=10,
        exposure="sheltered",
        site_surroundings="built_up",
    )
)
assert any("mono-pitch" in w.lower() for w in mono_resp.warnings)
assert any(
    "column util" in w.lower() or "low utilization" in w.lower()
    for w in mono_resp.warnings
)


print("PASS: test_proposal_tiers")



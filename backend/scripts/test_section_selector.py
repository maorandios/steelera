"""Section property + selector tests. Run: python scripts/test_section_selector.py"""



import sys

from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



from core.load_engine import _effective_load, compute_structural_recommendations

from core.preliminary_loads import estimate_preliminary_loads

from core.section_props import section_properties

from core.section_selector import select_column, select_truss_chord

from schemas.site import SiteContext



# --- section properties ---

ipe200 = section_properties("IPE200")

assert ipe200.area_mm2 > 2000

assert ipe200.wpl_y_mm3 > ipe200.wpl_z_mm3

shs150 = section_properties("SHS150x150x8")

assert shs150.area_mm2 > 4000

assert shs150.ry_mm > 50



# --- load estimates increase with load index ---

site_calm = SiteContext(

    latitude=51.5,

    longitude=-0.1,

    mean_wind_ms=5.5,

    design_wind_proxy_ms=7.5,

    terrain_class="IV",

    exposure="sheltered",

    load_index=6.9,

)

site_windy = SiteContext(

    latitude=25.2,

    longitude=55.3,

    mean_wind_ms=8.2,

    design_wind_proxy_ms=11.8,

    terrain_class="II",

    exposure="open",

    load_index=13.2,

)

load_calm = _effective_load(site_calm)

load_windy = _effective_load(site_windy)

assert load_calm >= 8.5

assert load_windy > load_calm



loads_calm = estimate_preliminary_loads(

    width_mm=12_000,

    length_mm=24_000,

    height_mm=5_000,

    roof_pitch_deg=10,

    bay_spacing_mm=6_000,

    effective_load_index=load_calm,

    site=site_calm,

)

loads_windy = estimate_preliminary_loads(

    width_mm=18_000,

    length_mm=36_000,

    height_mm=7_000,

    roof_pitch_deg=12,

    bay_spacing_mm=6_000,

    effective_load_index=load_windy,

    site=site_windy,

)

assert loads_windy.chord_axial_kn > loads_calm.chord_axial_kn

assert loads_windy.column_moment_knm > loads_calm.column_moment_knm



# --- selector picks valid catalog profiles ---

col_calm = select_column(loads_calm, height_mm=5_000, min_profile="HEA240")

assert col_calm.profile.startswith("HEA")

chord_windy = select_truss_chord(

    loads_windy,

    width_mm=18_000,

    bay_spacing_mm=6_000,

)

assert chord_windy.profile.startswith("SHS")



# --- integration with load engine (existing scenarios) ---

low_wind_open = SiteContext(

    latitude=31.25,

    longitude=34.79,

    mean_wind_ms=3.3,

    design_wind_proxy_ms=6.0,

    terrain_class="II",

    exposure="open",

    load_index=6.7,

)



calm_rec = compute_structural_recommendations(

    width_mm=12_000,

    length_mm=24_000,

    height_mm=5_000,

    roof_pitch_deg=10,

    site=site_calm,

)

assert calm_rec.use_truss is False

assert calm_rec.bay_spacing_mm == 6_000

assert calm_rec.column_profile == "HEA240"



windy_rec = compute_structural_recommendations(

    width_mm=18_000,

    length_mm=36_000,

    height_mm=7_000,

    roof_pitch_deg=12,

    site=site_windy,

)

assert windy_rec.use_truss is True

assert windy_rec.column_profile == "HEA400"

assert windy_rec.truss_chord_profile.startswith("SHS")
assert windy_rec.truss_web_profile



large_low_wind = compute_structural_recommendations(

    width_mm=18_000,

    length_mm=50_000,

    height_mm=8_000,

    roof_pitch_deg=10,

    site=low_wind_open,

)

assert large_low_wind.column_profile == "HEA300"

assert large_low_wind.truss_chord_profile == "SHS150x150x8"



print("PASS: test_section_selector")



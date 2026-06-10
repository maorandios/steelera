"""Load engine unit tests (no network). Run: python scripts/test_load_engine.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.load_engine import (
    _effective_load,
    compute_structural_recommendations,
)
from schemas.site import SiteContext

calm = SiteContext(
    latitude=51.5,
    longitude=-0.1,
    mean_wind_ms=5.5,
    design_wind_proxy_ms=7.5,
    terrain_class="IV",
    exposure="sheltered",
    load_index=6.9,
)

windy = SiteContext(
    latitude=25.2,
    longitude=55.3,
    mean_wind_ms=8.2,
    design_wind_proxy_ms=11.8,
    terrain_class="II",
    exposure="open",
    load_index=13.2,
)

low_wind_open = SiteContext(
    latitude=31.25,
    longitude=34.79,
    mean_wind_ms=3.3,
    design_wind_proxy_ms=6.0,
    terrain_class="II",
    exposure="open",
    load_index=6.7,
)

assert _effective_load(calm) >= 8.5
assert _effective_load(low_wind_open) >= 8.5

calm_rec = compute_structural_recommendations(
    width_mm=12_000,
    length_mm=24_000,
    height_mm=5_000,
    roof_pitch_deg=10,
    site=calm,
)
assert calm_rec.use_truss is False
assert calm_rec.bay_spacing_mm == 6_000
assert calm_rec.column_profile == "HEA240"

windy_rec = compute_structural_recommendations(
    width_mm=18_000,
    length_mm=36_000,
    height_mm=7_000,
    roof_pitch_deg=12,
    site=windy,
)
assert windy_rec.use_truss is True
assert windy_rec.bay_spacing_mm == 6_000
assert windy_rec.gable_bracing is True
assert windy_rec.roof_bracing is True
assert windy_rec.sag_rods is True
assert windy_rec.column_profile in (
    "HEA300", "HEA320", "HEA340", "HEA360", "HEA400",
)
assert windy_rec.truss_chord_profile.startswith("SHS")
assert windy_rec.truss_web_profile

large_low_wind = compute_structural_recommendations(
    width_mm=18_000,
    length_mm=50_000,
    height_mm=8_000,
    roof_pitch_deg=10,
    site=low_wind_open,
)
assert large_low_wind.use_truss is True
assert large_low_wind.column_profile in ("HEA300", "HEA320", "HEA340", "HEA360")
assert large_low_wind.truss_chord_profile == "SHS150x150x8"
assert large_low_wind.roof_bracing is True
assert large_low_wind.sag_rods is True
assert large_low_wind.bay_spacing_mm == 6_000

print("PASS: test_load_engine")

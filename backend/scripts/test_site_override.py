"""Site surroundings override tests. Run: python scripts/test_site_override.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.site_context import SiteContext, apply_surroundings_override

urban = SiteContext(
    latitude=31.25,
    longitude=34.79,
    location_label="Beer Sheva",
    mean_wind_ms=3.3,
    design_wind_proxy_ms=6.0,
    terrain_class="IV",
    exposure="sheltered",
    load_index=5.5,
    building_count_500m=40,
)

open_site = apply_surroundings_override(urban, "open_industrial")
assert open_site.terrain_class == "II"
assert open_site.exposure == "open"
assert open_site.load_index > urban.load_index
assert open_site.detected_terrain_class == "IV"
assert open_site.detected_load_index == 5.5
assert open_site.surroundings_applied == "open_industrial"

built = apply_surroundings_override(urban, "built_up")
assert built.terrain_class == "IV"
assert built.exposure == "sheltered"
assert built.surroundings_applied == "built_up"

print("PASS: test_site_override")

"""Unit checks for engineering_rules. Run: python scripts/test_engineering_rules.py"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engineering_rules import (
    WEB_ANGLE_MAX_DEG,
    WEB_ANGLE_MIN_DEG,
    gable_girt_roll_deg,
    generate_standard_pratt_webs,
    max_column_outside_half_on_x_line,
    max_column_outside_half_on_z_line,
    profile_column_outside_half_mm,
    sag_rod_bay_fractions,
    sag_rod_z_positions,
    wall_girt_roll_deg,
)

layout = generate_standard_pratt_webs(
    [0.0, 4000.0, 0.0],
    [8000.0, 9000.0, 0.0],
    800.0,
    bottom_end_y=4000.0,
    top_start_y=4000.0,
)
assert layout.panels >= 2
for web in layout.webs:
    if web.kind != "d":
        continue
    dx = abs(web.end[0] - web.start[0])
    dy = abs(web.end[1] - web.start[1])
    angle = math.degrees(math.atan2(dy, dx)) if dx > 1e-6 else 90.0
    assert WEB_ANGLE_MIN_DEG - 1 <= angle <= WEB_ANGLE_MAX_DEG + 1, angle

assert sag_rod_bay_fractions(5000) == [0.5]
assert sag_rod_bay_fractions(5500) == [0.5]
assert sag_rod_bay_fractions(5501) == [1.0 / 3.0, 2.0 / 3.0]

z_rows = sag_rod_z_positions(0.0, 6000.0, 6000.0)
assert len(z_rows) == 2
assert abs(z_rows[0] - 2000.0) < 1.0
assert abs(z_rows[1] - 4000.0) < 1.0

assert wall_girt_roll_deg(0.0, 12000.0) == 90.0
assert wall_girt_roll_deg(12000.0, 12000.0) == 270.0
assert gable_girt_roll_deg(0.0, 10000.0) == 270.0
assert gable_girt_roll_deg(10000.0, 10000.0) == 90.0

cols = {("A", "1"): "HEA200", ("A", "2"): "SHS300X300X10", ("J", "1"): "SHS300X300X10"}
assert max_column_outside_half_on_x_line("A", cols) == 150.0
assert profile_column_outside_half_mm("HEA200") == 100.0
assert profile_column_outside_half_mm("SHS300X300X10") == 150.0
z_cols = {("A", "1"): "HEA200", ("B", "1"): "SHS300X300X10", ("A+1/3", "1"): "HEA200"}
assert max_column_outside_half_on_z_line("1", z_cols) == 150.0

print("PASS: engineering_rules")

"""Unit checks for engineering_rules. Run: python scripts/test_engineering_rules.py"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engineering_rules import (
    PURLIN_APEX_CLEARANCE_MM,
    PURLIN_APEX_MIN_GAP_MM,
    WEB_ANGLE_MAX_DEG,
    WEB_ANGLE_MIN_DEG,
    duo_pitch_purlin_x_mm,
    gable_girt_roll_deg,
    generate_standard_pratt_webs,
    max_column_outside_half_on_x_line,
    max_column_outside_half_on_z_line,
    mono_pitch_purlin_x_mm,
    profile_column_outside_half_mm,
    purlin_distances_along_slope_mm,
    purlin_ridge_mirror_flag,
    purlin_roll_deg,
    purlin_seat_slope_offset_mm,
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

# --- Duo-pitch purlin layout ------------------------------------------------ #
pitch = math.radians(15.0)
cos_p = math.cos(pitch)
xs = duo_pitch_purlin_x_mm(12000.0, 6000.0, pitch, 1200.0)
assert xs[0] == 0.0 and abs(xs[-1] - 12000.0) < 1.0
left = [x for x in xs if x < 5999.0]
right = [x for x in xs if x > 6001.0]
assert len(left) == len(right)
left_d = [round(x / cos_p, 1) for x in left]
right_d = [round((12000.0 - x) / cos_p, 1) for x in reversed(right)]
assert left_d == right_d
assert all(abs(x - 6000.0) > 1.0 for x in xs)
seat = purlin_seat_slope_offset_mm(pitch)
# Last bay to apex < 300 mm — keep last spaced purlin, no ridge-adjacent extra.
assert abs(dists[-1] - 6000.0) < 1.0 if (dists := purlin_distances_along_slope_mm(6213.0, 1200.0, pitch_rad=pitch)) else False
assert (6213.0 - dists[-1]) < PURLIN_APEX_MIN_GAP_MM + 1.0
assert abs(max(left) / cos_p - 6000.0) < 5.0

# Large gap — add ridge-adjacent purlin at 100 mm from apex (seated).
long_dists = purlin_distances_along_slope_mm(9000.0, 1200.0, pitch_rad=pitch)
assert long_dists[-2] < long_dists[-1]
assert (9000.0 - long_dists[-2]) > PURLIN_APEX_MIN_GAP_MM
assert abs(long_dists[-1] - (9000.0 - PURLIN_APEX_CLEARANCE_MM + seat)) < 1.0

assert abs(purlin_roll_deg(pitch, 1.0) - 15.0) < 1e-6
assert abs(purlin_roll_deg(pitch, -1.0) + 15.0) < 1e-6
assert purlin_ridge_mirror_flag(3000.0, ridge_x_mm=6000.0, is_flat=False, is_mono=False) == 0.0
assert purlin_ridge_mirror_flag(9000.0, ridge_x_mm=6000.0, is_flat=False, is_mono=False) == 180.0

mono = mono_pitch_purlin_x_mm(10000.0, pitch, "B", 1200.0)
assert mono[0] == 0.0
mono_dists = purlin_distances_along_slope_mm(
    10000.0 / cos_p, 1200.0, pitch_rad=pitch
)
if (10000.0 / cos_p - mono_dists[-1]) > PURLIN_APEX_MIN_GAP_MM:
    assert abs((10000.0 - mono[-1]) / cos_p - (PURLIN_APEX_CLEARANCE_MM - seat)) < 1.0

print("PASS: engineering_rules")

"""Coverage for haunches, fly braces, base plates, bottom-chord restraint, purlin layout.

Run: python scripts/test_new_elements.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_member_catalog import members_from_grid_definition
from core.member_resolver import layout_to_macro_members
from core.geometry_engine import macro_members_to_project_elements
from schemas.spatial_grid import GridDefinition, StructuralGridLayout


def _build(**kw):
    gd = GridDefinition(
        x_spans=kw.pop("x_spans", [12000]),
        z_spans=kw.pop("z_spans", [5000, 5000, 5000]),
        height_mm=4000,
        roof_pitch_deg=kw.pop("pitch", 15.0),
        roof_style=kw.pop("style", "duo_pitch"),
        **kw,
    )
    members = members_from_grid_definition(gd)
    layout = StructuralGridLayout(grid_definition=gd, structural_members=members)
    macro = layout_to_macro_members(layout)
    elements = macro_members_to_project_elements(macro)
    return members, macro, elements


def _finite(elements) -> bool:
    for e in elements:
        for pt in (e.nodes or {}).values():
            if not all(isinstance(v, (int, float)) and v == v for v in pt):
                return False
        for v in e.size_mm.values():
            if not (isinstance(v, (int, float)) and v == v):
                return False
    return True


def _by_type(macro, et):
    return [m for m in macro if m.get("element_type") == et]


# --- Duo-pitch purlins: mirrored slopes, apex clearance, no ridge seat ------- #
_, macro, _ = _build()
purlins = _by_type(macro, "purlin")
assert purlins, "no purlins"
xs = sorted({round(m["nodes"]["start"][0], 1) for m in purlins})
mid = 6000.0  # 12 m span → ridge at 6 m
pitch = math.radians(15.0)
cos_p = math.cos(pitch)
# Eave purlins at both outer X lines (0 and 12000).
assert any(abs(x - 0.0) < 50.0 for x in xs), f"no left eave purlin: {xs}"
assert any(abs(x - 12000.0) < 50.0 for x in xs), f"no right eave purlin: {xs}"
# No purlin on the ridge itself.
assert all(abs(x - mid) > 50.0 for x in xs), f"purlin on ridge: {xs}"
eave_l, eave_r = min(xs), max(xs)
left = [x for x in xs if x < mid - 1.0]
right = [x for x in xs if x > mid + 1.0]
assert len(left) == len(right), f"unequal purlin count per slope: {left} vs {right}"
left_d = [round((x - eave_l) / cos_p, 1) for x in left]
right_d = [round((eave_r - x) / cos_p, 1) for x in reversed(right)]
assert left_d == right_d, f"purlins not mirrored: {left_d} vs {right_d}"
# Last bay < 300 mm to apex — no extra ridge purlin; innermost stays on spacing grid.
inner_left = max(left)
inner_right = min(right)
gap_left = (mid - inner_left) / cos_p
assert 200.0 < gap_left < 280.0, gap_left
assert abs(gap_left - (inner_right - mid) / cos_p) < 2.0
# Right-slope purlins carry a mirror flag (Y-Euler) for face-to-face C-profile rendering.
left_p = next(m for m in purlins if abs(m["nodes"]["start"][0] - inner_left) < 5.0)
right_p = next(m for m in purlins if abs(m["nodes"]["start"][0] - inner_right) < 5.0)
assert left_p["rotation"][1] == 0.0, left_p["rotation"]
assert right_p["rotation"][1] == 180.0, right_p["rotation"]
assert abs(left_p["nodes"]["start"][1] - right_p["nodes"]["start"][1]) < 5.0
# Face-to-face mirror about the ridge (resolved seating may shift eaves slightly).
for lx, rx in zip(left, reversed(right)):
    assert abs((mid - lx) - (rx - mid)) < 2.0, (lx, rx)

# --- Haunches (rafter scheme) ---------------------------------------------- #
_, macro, elements = _build(haunches=True)
haunch_m = _by_type(macro, "haunch")
assert len(haunch_m) >= 4, f"expected ≥4 haunches (eave+apex per slope per frame): {len(haunch_m)}"
hel = [e for e in elements if e.element_type == "haunch"]
assert hel and all(e.shape_type == "Haunch" for e in hel), "haunch shape_type"
assert all(e.taper_end_depth_mm and e.depth_mm > e.taper_end_depth_mm for e in hel), "haunch taper"
assert all(m["length"] >= 1.0 for m in haunch_m), "degenerate haunch"

# --- Base plates ----------------------------------------------------------- #
_, macro, elements = _build(base_plates=True)
plate_m = _by_type(macro, "base_plate")
assert plate_m, "no base plates"
pel = [e for e in elements if e.element_type == "base_plate"]
assert all(e.shape_type == "Plate" for e in pel), "plate shape_type"
assert all(e.size_mm["y"] > 0 and e.size_mm["x"] > 0 and e.size_mm["z"] > 0 for e in pel), "plate dims"
# One per main column (2 x-lines × 4 z-lines = 8) at minimum.
assert len(plate_m) >= 8, f"too few base plates: {len(plate_m)}"

# --- Fly braces ------------------------------------------------------------ #
_, macro, _ = _build(fly_braces=True)
fly_m = _by_type(macro, "fly_brace")
purlin_n = len(_by_type(macro, "purlin"))
frame_n = len(GridDefinition(
    x_spans=[12000], z_spans=[5000, 5000, 5000], height_mm=4000,
    roof_pitch_deg=15, roof_style="duo_pitch",
).z_spans) + 1
assert len(fly_m) == purlin_n * frame_n * 2, (len(fly_m), purlin_n, frame_n)
assert fly_m, "no fly braces"
assert all(m["length"] >= 1.0 for m in fly_m), "degenerate fly brace"
for m in fly_m:
    s, e = m["nodes"]["start"], m["nodes"]["end"]
    dx, dy, dz = e[0] - s[0], e[1] - s[1], e[2] - s[2]
    assert dy > 50.0, (m["id"], dy)  # rises to purlin bottom
    assert abs(dz) > 50.0, (m["id"], dz)  # V leg along purlin run
    assert abs(dz) > abs(dx), (m["id"], dx, dz)  # not a slope-parallel stub

# --- Sag rods pierce girts/purlins at section centre ----------------------- #
_, macro, _ = _build(
    use_truss=True,
    truss_type="pratt",
    sag_rods=True,
    column_profile="UC203x203x46",
    girt_profile="Z200x2.5",
    purlin_profile="Z200x2.5",
)
girts = {m["id"]: m for m in macro if m.get("element_type") == "wall_girt"}
sags = [m for m in macro if m.get("element_type") == "sag_rod"]
assert sags, "no sag rods"
for sag in sags:
    if "-sag-wall-" not in sag["id"]:
        continue
    wall = "A" if "-sag-wall-A-" in sag["id"] else "B"
    level = sag["id"].split("-")[-1]
    girt = girts.get(f"shed_1-girt-{wall}-L{level}")
    assert girt, (sag["id"], wall, level)
    assert abs(sag["nodes"]["start"][0] - girt["nodes"]["start"][0]) < 1.0, (
        sag["id"],
        sag["nodes"]["start"][0],
        girt["nodes"]["start"][0],
    )
roof_sags = [
    m for m in sags if abs(m["nodes"]["start"][0] - m["nodes"]["end"][0]) > 100.0
]
purlins = sorted(
    [m for m in macro if m.get("element_type") == "purlin"],
    key=lambda m: m["nodes"]["start"][0],
)
if roof_sags and len(purlins) >= 2:
    sag = roof_sags[0]
    sx = sag["nodes"]["start"][0]
    near = min(purlins, key=lambda p: abs(p["nodes"]["start"][0] - sx))
    cy = (near["nodes"]["start"][1] + near["nodes"]["end"][1]) / 2.0
    assert abs(sag["nodes"]["start"][1] - cy) < 120.0, (
        sag["id"],
        sag["nodes"]["start"][1],
        cy,
    )

# --- Bottom-chord restraint (needs trusses) -------------------------------- #
_, macro, _ = _build(use_truss=True, truss_type="pratt", bottom_chord_restraint=True)
bc = [m for m in macro if "bctie" in str(m.get("id", ""))]
assert len(bc) >= 2, f"no bottom-chord restraint: {len(bc)}"

# --- Everything together is finite ----------------------------------------- #
_, macro, elements = _build(
    haunches=True, fly_braces=True, base_plates=True,
    sag_rods=True, x_bracing=True, roof_bracing=True, gable_bracing=True,
)
assert _finite(elements), "non-finite geometry in combined build"

# Mono + flat: haunches/plates/fly still finite (apex haunch only on duo).
for style, pitch in (("mono_pitch", 10.0), ("flat", 0.0)):
    _, macro, elements = _build(style=style, pitch=pitch, haunches=True, base_plates=True, fly_braces=True)
    assert _finite(elements), (style, "non-finite")

# --- Legacy request path (chat checklist / sidebar) threads the flags --------- #
from schemas.macro import GenerateShedRequest
from core.shed_config_bridge import legacy_request_to_config
from core.grid_member_catalog import members_from_shed_config

req = GenerateShedRequest.model_validate(
    {
        "assembly_id": "shed_1",
        "x_spans": [12000],
        "z_spans": [5000, 5000, 5000],
        "height": 4000,
        "roof_pitch_deg": 15,
        "roof_style": "duo_pitch",
        "use_haunches": True,
        "use_fly_braces": True,
        "use_base_plates": True,
    }
)
cfg = legacy_request_to_config(req)
assert cfg.haunches and cfg.fly_braces and cfg.base_plates, "legacy flags not threaded"
mem = members_from_shed_config(cfg)
ets = {m.element_type for m in mem}
assert "haunch" in ets and "fly_brace" in ets and "base_plate" in ets, ets

print("PASS: new elements")
print(f"  ridge/eave purlins X set: {xs}")
print(f"  haunches={len(haunch_m)} base_plates={len(plate_m)} fly_braces={len(fly_m)} bctie={len(bc)}")

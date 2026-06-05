"""Coverage for haunches, fly braces, base plates, bottom-chord restraint, ridge purlin.

Run: python scripts/test_new_elements.py
"""

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


# --- Ridge purlin guarantee (duo pitch, ridge between grid lines) ---------- #
_, macro, _ = _build()
purlins = _by_type(macro, "purlin")
assert purlins, "no purlins"
# A purlin must sit at the apex X (ridge) — its X equals the ridge x within tol.
ridge_x = max(m["nodes"]["start"][0] for m in purlins)  # any
xs = sorted({round(m["nodes"]["start"][0], 1) for m in purlins})
mid = 6000.0  # 12 m span → ridge at 6 m
assert any(abs(x - mid) < 50.0 for x in xs), f"no ridge purlin near {mid}: {xs}"
# Eave purlins at both outer X lines (0 and 12000).
assert any(abs(x - 0.0) < 50.0 for x in xs), f"no left eave purlin: {xs}"
assert any(abs(x - 12000.0) < 50.0 for x in xs), f"no right eave purlin: {xs}"

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

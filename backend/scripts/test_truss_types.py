"""Truss web-pattern registry coverage. Run: python scripts/test_truss_types.py"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.grid_member_catalog import members_from_grid_definition
from core.member_resolver import layout_to_macro_members
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

DUO_TYPES = ["pratt", "howe", "warren", "fink", "king_post", "queen_post", "scissor"]


def _build(style: str, pitch: float, truss_type: str) -> tuple[list, list[dict]]:
    gd = GridDefinition(
        x_spans=[12000],
        z_spans=[5000, 5000, 5000],
        height_mm=4000,
        roof_pitch_deg=pitch,
        roof_style=style,
        use_truss=True,
        truss_type=truss_type,
    )
    members = members_from_grid_definition(gd)
    layout = StructuralGridLayout(grid_definition=gd, structural_members=members)
    macro = layout_to_macro_members(layout)
    return members, macro


def _resolved_webs(macro: list[dict]) -> list[dict]:
    return [m for m in macro if "truss-web" in str(m.get("id", ""))]


def _finite(macro: list[dict]) -> bool:
    for m in macro:
        nodes = m.get("nodes") or {}
        for pt in nodes.values():
            if not all(isinstance(v, (int, float)) and v == v for v in pt):
                return False
    return True


# Every duo-pitch truss type must produce chords + at least one resolved web,
# with finite geometry and no degenerate (zero-length) leftovers.
for t in DUO_TYPES:
    members, macro = _build("duo_pitch", 15.0, t)
    chords = [m for m in members if m.element_type == "truss_chord"]
    rweb = _resolved_webs(macro)
    assert len(chords) >= 3, (t, len(chords))
    assert len(rweb) > 0, (t, "no resolved webs")
    assert _finite(macro), (t, "non-finite geometry")
    # No truss member should be shorter than 1 mm after resolution.
    for m in macro:
        if "truss" in str(m.get("id", "")):
            assert m["length"] >= 1.0, (t, m["id"], m["length"])

# Scissor adds an extra (kinked) bottom chord vs a flat-tie truss.
fink_chords = [m for m in _build("duo_pitch", 15.0, "fink")[0] if m.element_type == "truss_chord"]
scissor_chords = [m for m in _build("duo_pitch", 15.0, "scissor")[0] if m.element_type == "truss_chord"]
assert len(scissor_chords) > len(fink_chords), (len(scissor_chords), len(fink_chords))

# Fink: inner W only — 4 diagonals (no outer heel→rafter-mid struts).
from core.engineering_rules import fink_truss_web_plan, truss_web_plan

_fink_plan = fink_truss_web_plan(6, 3)
assert len(_fink_plan) == 4, len(_fink_plan)
assert fink_truss_web_plan(6, 3) == truss_web_plan("fink", 6, 3)
assert (("bottom", 0), ("top", 1)) not in _fink_plan
assert (("top", 5), ("bottom", 6)) not in _fink_plan
assert (("top", 1), ("bottom", 2)) in _fink_plan
assert (("bottom", 2), ("top", 3)) in _fink_plan
assert (("top", 3), ("bottom", 4)) in _fink_plan
assert (("bottom", 4), ("top", 5)) in _fink_plan
_, _fink_macro = _build("duo_pitch", 12.0, "fink")
_fink_webs = [
    m
    for m in _fink_macro
    if m.get("element_type") == "truss_web"
    and m["id"].startswith("shed_1-truss-web-1-")
]
assert len(_fink_webs) == 4, ("fink should have 4 inner web diagonals", len(_fink_webs))
_fink_posts = [m for m in _fink_macro if "truss-post-1-" in m["id"]]
assert len(_fink_posts) >= 2, "fink still needs portal end posts"
for w in _fink_webs:
    x0, y0 = w["nodes"]["start"][0], w["nodes"]["start"][1]
    x1, y1 = w["nodes"]["end"][0], w["nodes"]["end"][1]
    angle = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
    assert 8.0 <= angle <= 70.0, (w["id"], angle)

# Apex-only patterns gracefully fall back to Pratt on mono/flat roofs.
for style, pitch in (("mono_pitch", 12.0), ("flat", 0.0)):
    for t in ("fink", "scissor", "pratt", "warren"):
        members, macro = _build(style, pitch, t)
        assert len(_resolved_webs(macro)) > 0, (style, t)
        assert _finite(macro), (style, t)

# Normalization: aliases + suffixes resolve to canonical types.
gd = GridDefinition(
    x_spans=[10000], z_spans=[5000], height_mm=4000, roof_pitch_deg=10,
    use_truss=True, truss_type="Howe Truss",
)
assert gd.truss_type == "howe", gd.truss_type
gd = GridDefinition(
    x_spans=[10000], z_spans=[5000], height_mm=4000, roof_pitch_deg=10,
    use_truss=True, truss_type="kingpost",
)
assert gd.truss_type == "king_post", gd.truss_type

# Scissor: bottom-chord ties follow the raised bottom chord (not eave level).
gd_scissor = GridDefinition(
    x_spans=[14000],
    z_spans=[5000, 5000, 5000],
    height_mm=5000,
    roof_pitch_deg=18,
    roof_style="duo_pitch",
    use_truss=True,
    truss_type="scissor",
    bottom_chord_restraint=True,
    roof_bracing=True,
)
members = members_from_grid_definition(gd_scissor)
layout = StructuralGridLayout(grid_definition=gd_scissor, structural_members=members)
macro = layout_to_macro_members(layout)
bcties = [m for m in macro if "bctie" in str(m.get("id", ""))]
assert bcties, "no bottom-chord restraint ties"
for m in bcties:
    y = m["nodes"]["start"][1]
    assert y > 5200.0, (m["id"], y)
roof_braces = [m for m in macro if "brace-roof-s" in str(m.get("id", ""))]
assert len(roof_braces) == 0, ("truss end bays should not get rafter-style roof X", len(roof_braces))

# Scissor shed: no fly braces / gable X-bracing on truss frames; girts bay-sized.
gd_scissor_full = GridDefinition(
    x_spans=[12000],
    z_spans=[5000, 5000, 5000],
    height_mm=5000,
    roof_pitch_deg=18,
    roof_style="duo_pitch",
    use_truss=True,
    truss_type="scissor",
    generate_wall_girts=True,
    fly_braces=True,
    gable_bracing=True,
    roof_bracing=True,
)
macro_full = layout_to_macro_members(
    StructuralGridLayout(
        grid_definition=gd_scissor_full,
        structural_members=members_from_grid_definition(gd_scissor_full),
    )
)
assert not [m for m in macro_full if m.get("element_type") == "fly_brace"], "fly braces on truss frames"
assert not [m for m in macro_full if m.get("id", "").endswith("end-1-a")], "gable X on truss"
assert not [m for m in macro_full if "-brace-A-" in m.get("id", "")], "side-wall X on truss bays"
assert not [m for m in macro_full if "brace-roof-s" in m.get("id", "")], "roof X on truss bays"
gable_girts = [m for m in macro_full if "gablegirt" in str(m.get("id", ""))]
assert gable_girts, "no gable girts"
assert all(abs(m["nodes"]["start"][0] - m["nodes"]["end"][0]) < 7000 for m in gable_girts), (
    "full-width gable girt",
    max(abs(m["nodes"]["start"][0] - m["nodes"]["end"][0]) for m in gable_girts),
)

# Stale AI/hand members with bracing must not survive truss catalog resolution.
from core.grid_layout_utils import ensure_layout_members
from schemas.spatial_grid import GridNodeReference, StructuralMember

stale = StructuralMember(
    id="shed_1-brace-roof-s0-b0-a",
    element_type="bracing",
    profile="L50x50",
    start_node=GridNodeReference(x_axis="A", z_axis="1", elevation="eave"),
    end_node=GridNodeReference(x_axis="A+1/4", z_axis="2", elevation="roof"),
)
layout_stale = StructuralGridLayout(
    grid_definition=gd_scissor_full,
    structural_members=[stale],
)
fresh = ensure_layout_members(layout_stale)
assert not any(m.element_type == "bracing" for m in fresh.structural_members), "stale truss bracing"

# Mono-pitch truss: every frame uses the same panelled Pratt webs (no gable shortcut).
import math


def _is_vertical_web(member: dict) -> bool:
    nodes = member.get("nodes") or {}
    start = nodes.get("start") or [0, 0, 0]
    end = nodes.get("end") or [0, 0, 0]
    dx = abs(start[0] - end[0])
    dy = abs(start[1] - end[1])
    dz = abs(start[2] - end[2])
    return dy > 50.0 and dx < 50.0 and dz < 50.0


def _end_vertical_webs(macro: list[dict], frame_prefix: str) -> list[dict]:
    return [
        m
        for m in macro
        if str(m.get("id", "")).startswith(frame_prefix)
        and ("truss-web" in str(m.get("id", "")) or "truss-post" in str(m.get("id", "")))
        and _is_vertical_web(m)
    ]


def _portal_end_posts(macro: list[dict], frame_prefix: str) -> list[dict]:
    """End verticals between TC and BC — must match bottom-chord section."""
    posts = _end_vertical_webs(macro, frame_prefix)
    frame_z = frame_prefix.split("-")[-2]
    posts.extend(
        m
        for m in macro
        if str(m.get("id", "")).startswith(f"shed_1-truss-post-{frame_z}-")
        and _is_vertical_web(m)
    )
    return [m for m in posts if m.get("element_type") == "truss_chord"]

gd_mono_truss = GridDefinition(
    x_spans=[12000],
    z_spans=[5000, 5000, 5000],
    height_mm=4000,
    roof_pitch_deg=10,
    roof_style="mono_pitch",
    mono_high_side="B",
    use_truss=True,
    truss_type="pratt",
    generate_wall_girts=True,
)
mono_members = members_from_grid_definition(gd_mono_truss)
mono_macro = layout_to_macro_members(
    StructuralGridLayout(
        grid_definition=gd_mono_truss,
        structural_members=mono_members,
    )
)
# Every portal frame gets the same multi-panel web layout.
frame1_webs = [m for m in mono_members if m.id.startswith("shed_1-truss-web-1-")]
frame2_webs = [m for m in mono_members if m.id.startswith("shed_1-truss-web-2-")]
frame3_webs = [m for m in mono_members if m.id.startswith("shed_1-truss-web-3-")]
assert len(frame1_webs) == len(frame2_webs) == len(frame3_webs), (
    len(frame1_webs),
    len(frame2_webs),
    len(frame3_webs),
)
assert len(frame1_webs) >= 5, len(frame1_webs)
diagonal_webs = [
    m
    for m in mono_macro
    if m["id"].startswith("shed_1-truss-web-1-")
    and m.get("element_type") == "truss_web"
    and not _is_vertical_web(m)
]
assert diagonal_webs, "mono truss frame missing interior panel diagonals"
high_gable_col = next(m for m in mono_macro if m["id"] == "shed_1-col-B-1")
assert abs(high_gable_col["length"] - 4000.0) < 2.0, high_gable_col["length"]

mono_bc_profile = next(
    m["profile"] for m in mono_macro if m["id"] == "shed_1-truss-bc-1-0"
)
mono_end_posts = _portal_end_posts(mono_macro, "shed_1-truss-web-1-")
assert len(mono_end_posts) >= 2, len(mono_end_posts)
low_post = next(m for m in mono_macro if m["id"] == "shed_1-truss-post-1-low")
high_post = next(m for m in mono_macro if m["id"] == "shed_1-truss-post-1-high")
assert low_post["length"] < high_post["length"], (
    low_post["length"],
    high_post["length"],
)
for post in mono_end_posts:
    assert post["profile"] == mono_bc_profile, (post["id"], post["profile"])
assert low_post["length"] >= 250.0, (low_post["id"], low_post["length"])
assert high_post["length"] >= 1500.0, (high_post["id"], high_post["length"])

mono_tc_frame1 = [m for m in mono_macro if m["id"].startswith("shed_1-truss-tc-1-")]
mono_bc_frame1 = [m for m in mono_macro if m["id"].startswith("shed_1-truss-bc-1-")]
assert len(mono_tc_frame1) == 1, ("mono TC should be one continuous beam", len(mono_tc_frame1))
assert len(mono_bc_frame1) == 1, ("mono BC should be one continuous beam", len(mono_bc_frame1))

# Purlins seat on truss TC (local segment pitch), not floating at natural roof height.
from core.grid_member_catalog import truss_top_chord_y_at_x
from core.spatial_grid import StructuralGridEngine

_mono_grid = StructuralGridEngine.from_definition(gd_mono_truss)
_purlins = [m for m in mono_macro if m.get("element_type") == "purlin"]
assert _purlins, "no purlins on mono truss shed"
_p0 = max(_purlins, key=lambda m: m["nodes"]["start"][0])
_sample_x = _p0["nodes"]["start"][0]
_tc_y = truss_top_chord_y_at_x(_mono_grid, _sample_x)
_purlin_y = min(_p0["nodes"]["start"][1], _p0["nodes"]["end"][1])
_natural_roof_y = _mono_grid.roof.eave_y + _sample_x * math.tan(
    _mono_grid.roof.pitch_rad
)
assert _purlin_y > _tc_y - 5.0, ("purlin below TC", _purlin_y, _tc_y)
assert _purlin_y - _tc_y < 220.0, ("purlin too far above TC", _purlin_y, _tc_y)
assert abs(_purlin_y - _natural_roof_y) > 50.0, (
    "purlin still at natural roof not TC",
    _purlin_y,
    _natural_roof_y,
)

tc0 = next(m for m in mono_macro if m["id"] == "shed_1-truss-tc-1-0")
bc0 = next(m for m in mono_macro if m["id"] == "shed_1-truss-bc-1-0")
low_post = next(m for m in mono_macro if m["id"] == "shed_1-truss-post-1-low")
assert abs(tc0["nodes"]["start"][1] - low_post["nodes"]["start"][1]) < 1.0, (
    "end post top must share TC centerline node",
    tc0["nodes"]["start"][1],
    low_post["nodes"]["start"][1],
)
assert abs(bc0["nodes"]["start"][1] - low_post["nodes"]["end"][1]) < 1.0, (
    "end post bottom must share BC centerline node",
    bc0["nodes"]["start"][1],
    low_post["nodes"]["end"][1],
)
assert abs(low_post["nodes"]["start"][0] - tc0["nodes"]["start"][0]) < 1.0
assert tc0["nodes"]["end"][1] > tc0["nodes"]["start"][1], (
    "mono TC must slope up toward the high side",
    tc0["nodes"],
)
assert tc0["length"] > 11000.0, ("mono TC should span the full frame", tc0["length"])

# Duo-pitch Pratt: both eave ends need resolved vertical end posts (TC above BC).
_, duo_macro = _build("duo_pitch", 10.0, "pratt")
duo_end_verticals = _end_vertical_webs(duo_macro, "shed_1-truss-web-1-")
duo_end_posts = _portal_end_posts(duo_macro, "shed_1-truss-web-1-")
assert len(duo_end_posts) >= 2, len(duo_end_posts)
duo_left_post = next(
    m for m in duo_macro if m["id"] == "shed_1-truss-post-1-0"
)
duo_right_post = next(
    m for m in duo_macro if m["id"].startswith("shed_1-truss-post-1-") and m["id"] != "shed_1-truss-post-1-0"
)
assert duo_left_post["element_type"] == "truss_chord", duo_left_post
assert duo_right_post["element_type"] == "truss_chord", duo_right_post
assert duo_left_post["length"] >= 200.0, duo_left_post["length"]
assert duo_right_post["length"] >= 200.0, duo_right_post["length"]
duo_tc_left = next(m for m in duo_macro if m["id"] == "shed_1-truss-tc-1-0")
duo_bc = next(m for m in duo_macro if m["id"] == "shed_1-truss-bc-1-0")
assert abs(duo_left_post["nodes"]["start"][1] - duo_tc_left["nodes"]["start"][1]) < 1.0
assert abs(duo_left_post["nodes"]["end"][1] - duo_bc["nodes"]["start"][1]) < 1.0
assert abs(duo_left_post["nodes"]["start"][0] - duo_tc_left["nodes"]["start"][0]) < 1.0

# Duo TC panel nodes must follow the straight heel→ridge chord (never dip below the heel).
from core.grid_member_catalog import (
    _truss_top_chord_panel_xy,
    truss_pitch_at_x,
    truss_top_chord_y_at_x,
)
from core.engineering_rules import (
    profile_half_depth_mm,
    seat_purlin_bottom_on_rafter,
    seat_web_on_top_chord_bottom,
)
from core.spatial_grid import StructuralGridEngine

_duo_gd = GridDefinition(
    x_spans=[12000],
    z_spans=[5000, 5000, 5000],
    height_mm=4000,
    roof_pitch_deg=10,
    roof_style="duo_pitch",
    use_truss=True,
    truss_type="pratt",
)
_duo_grid = StructuralGridEngine.from_definition(_duo_gd)
_duo_xs, _duo_ys = _truss_top_chord_panel_xy(_duo_grid)
assert _duo_ys[1] >= _duo_ys[0] - 1.0, ("TC dips below heel", _duo_ys[0], _duo_ys[1])
assert truss_pitch_at_x(_duo_grid, 0.0)[1] > 0, truss_pitch_at_x(_duo_grid, 0.0)

_half = profile_half_depth_mm("IPE200")
_duo_webs = [
    m
    for m in duo_macro
    if m.get("element_type") == "truss_web"
    and m["id"].startswith("shed_1-truss-web-1-")
]
assert _duo_webs, "duo webs missing"
for w in _duo_webs:
    sy = w["nodes"]["start"][1]
    ey = w["nodes"]["end"][1]
    top_x = w["nodes"]["start"][0] if sy > ey else w["nodes"]["end"][0]
    top_y = max(sy, ey)
    tc_y = truss_top_chord_y_at_x(_duo_grid, top_x)
    pitch = truss_pitch_at_x(_duo_grid, top_x)
    tc_bottom = seat_web_on_top_chord_bottom(
        top_x,
        tc_y,
        0.0,
        chord_profile="IPE200",
        pitch_rad=pitch[0],
        pitch_sign=pitch[1],
    )[1]
    assert abs(top_y - tc_bottom) < 2.0, (w["id"], top_y, tc_bottom)

_duo_p0 = next(m for m in duo_macro if m["id"] == "shed_1-purlin-0")
_px = _duo_p0["nodes"]["start"][0]
_tc_y = truss_top_chord_y_at_x(_duo_grid, _px)
_pp = truss_pitch_at_x(_duo_grid, _px)
_seated = seat_purlin_bottom_on_rafter(
    _px,
    _tc_y,
    0.0,
    rafter_profile="IPE200",
    pitch_rad=_pp[0],
    pitch_sign=_pp[1],
)[1]
assert abs(_duo_p0["nodes"]["start"][1] - _seated) < 2.0, (
    "eave purlin must sit on TC top flange",
    _duo_p0["nodes"]["start"][1],
    _seated,
)

# King-post: central vertical + two struts from BC centre (all web profile).
from core.engineering_rules import (
    KING_POST_STRUT_ANGLE_MAX_DEG,
    KING_POST_STRUT_ANGLE_MIN_DEG,
    king_post_truss_web_plan,
)

_king_plan = king_post_truss_web_plan(4, 2)
assert len(_king_plan) == 3, len(_king_plan)
assert king_post_truss_web_plan(4, 2) == truss_web_plan("king_post", 4, 2)
assert (("bottom", 2), ("top", 2)) in _king_plan
assert (("bottom", 2), ("top", 1)) in _king_plan
assert (("bottom", 2), ("top", 3)) in _king_plan

_, king_macro = _build("duo_pitch", 12.0, "king_post")
_king_webs = [
    m
    for m in king_macro
    if m.get("element_type") == "truss_web"
    and m["id"].startswith("shed_1-truss-web-1-")
]
assert len(_king_webs) == 3, ("king-post needs 3 web members", len(_king_webs))
for w in _king_webs:
    assert w["profile"] == "L50x50", w
assert not any(m["id"].startswith("shed_1-truss-king-") for m in king_macro)
_king_vertical = next(
    w
    for w in _king_webs
    if abs(w["nodes"]["start"][0] - w["nodes"]["end"][0]) < 1.0
)
assert abs(_king_vertical["nodes"]["start"][1] - _king_vertical["nodes"]["end"][1]) > 200
for w in _king_webs:
    if w is _king_vertical:
        continue
    dx = abs(w["nodes"]["end"][0] - w["nodes"]["start"][0])
    dy = abs(w["nodes"]["end"][1] - w["nodes"]["start"][1])
    if dx > 1.0:
        strut_deg = math.degrees(math.atan2(dy, dx))
        assert KING_POST_STRUT_ANGLE_MIN_DEG <= strut_deg <= KING_POST_STRUT_ANGLE_MAX_DEG, (
            w["id"],
            strut_deg,
        )
king_tc = [m for m in king_macro if m["id"].startswith("shed_1-truss-tc-1-")]
assert king_tc, "king-post TC missing"
for seg in king_tc:
    y0, y1 = seg["nodes"]["start"][1], seg["nodes"]["end"][1]
    x0, x1 = seg["nodes"]["start"][0], seg["nodes"]["end"][0]
    if abs(x1 - x0) > 100:
        pitch = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
        assert pitch > 5.0, (seg["id"], pitch)

# Queen-post: central box (two verticals + straining beam) + wing struts (n=6).
from core.engineering_rules import queen_post_truss_web_plan

_queen_plan = queen_post_truss_web_plan(6, 3)
assert len(_queen_plan) == 5, len(_queen_plan)
assert queen_post_truss_web_plan(6, 3) == truss_web_plan("queen_post", 6, 3)
assert (("bottom", 2), ("top", 2)) in _queen_plan
assert (("bottom", 4), ("top", 4)) in _queen_plan
assert (("top", 2), ("top", 4)) in _queen_plan
assert (("bottom", 2), ("top", 1)) in _queen_plan
assert (("bottom", 4), ("top", 5)) in _queen_plan
_, _queen_macro = _build("duo_pitch", 12.0, "queen_post")
_queen_webs = [
    m
    for m in _queen_macro
    if m.get("element_type") == "truss_web"
    and m["id"].startswith("shed_1-truss-web-1-")
]
assert len(_queen_webs) == 5, ("queen-post needs 5 web members", len(_queen_webs))
for w in _queen_webs:
    assert w["profile"] == "L50x50", w
_queen_verticals = [
    w
    for w in _queen_webs
    if abs(w["nodes"]["start"][0] - w["nodes"]["end"][0]) < 1.0
]
assert len(_queen_verticals) == 2, len(_queen_verticals)
for w in _queen_verticals:
    assert abs(w["nodes"]["start"][1] - w["nodes"]["end"][1]) > 200, w["id"]
_straining = [
    w
    for w in _queen_webs
    if abs(w["nodes"]["start"][1] - w["nodes"]["end"][1]) < 2.0
    and abs(w["nodes"]["start"][0] - w["nodes"]["end"][0]) > 500
]
assert len(_straining) == 1, len(_straining)
_wing_struts = [w for w in _queen_webs if w not in _queen_verticals and w not in _straining]
assert len(_wing_struts) == 2, len(_wing_struts)
for w in _wing_struts:
    dx = abs(w["nodes"]["end"][0] - w["nodes"]["start"][0])
    dy = abs(w["nodes"]["end"][1] - w["nodes"]["start"][1])
    if dx > 1.0:
        wing_deg = math.degrees(math.atan2(dy, dx))
        assert 20.0 <= wing_deg <= 70.0, (w["id"], wing_deg)

# Scissor (and all apex types) must get the same explicit portal end posts as Pratt.
from core.engineering_rules import scissor_truss_web_plan

_scissor_plan = scissor_truss_web_plan(4, 2)
assert len(_scissor_plan) == 4, len(_scissor_plan)
assert scissor_truss_web_plan(4, 2) == truss_web_plan("scissor", 4, 2)
assert (("bottom", 1), ("top", 2)) in _scissor_plan
assert (("bottom", 3), ("top", 2)) in _scissor_plan
assert (("bottom", 1), ("top", 3)) in _scissor_plan
assert (("bottom", 3), ("top", 1)) in _scissor_plan
_, scissor_macro = _build("duo_pitch", 18.0, "scissor")
_scissor_webs = [
    m
    for m in scissor_macro
    if m.get("element_type") == "truss_web"
    and m["id"].startswith("shed_1-truss-web-1-")
]
assert len(_scissor_webs) == 4, ("scissor needs 4 triangulation webs", len(_scissor_webs))
for w in _scissor_webs:
    assert w["profile"] == "L50x50", w
_scissor_tc = [m for m in scissor_macro if m["id"].startswith("shed_1-truss-tc-1-")]
_scissor_bc = [m for m in scissor_macro if m["id"].startswith("shed_1-truss-bc-1-")]
assert len(_scissor_tc) == 2 and len(_scissor_bc) == 2, (
    "scissor needs split TC/BC at apex",
    len(_scissor_tc),
    len(_scissor_bc),
)
for seg in _scissor_tc:
    x0, y0 = seg["nodes"]["start"][0], seg["nodes"]["start"][1]
    x1, y1 = seg["nodes"]["end"][0], seg["nodes"]["end"][1]
    if abs(x1 - x0) > 500:
        tc_pitch = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
        break
else:
    tc_pitch = 0.0
for seg in _scissor_bc:
    x0, y0 = seg["nodes"]["start"][0], seg["nodes"]["start"][1]
    x1, y1 = seg["nodes"]["end"][0], seg["nodes"]["end"][1]
    if abs(x1 - x0) > 500:
        bc_pitch = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
        break
else:
    bc_pitch = 0.0
assert tc_pitch > 5.0, tc_pitch
assert bc_pitch > 2.0, bc_pitch
assert abs(bc_pitch - tc_pitch * 0.5) < 3.0, (bc_pitch, tc_pitch)
_bc_center_y = next(m for m in scissor_macro if m["id"] == "shed_1-truss-bc-1-0")[
    "nodes"
]["end"][1]
_bc_heel_y = next(m for m in scissor_macro if m["id"] == "shed_1-truss-bc-1-0")[
    "nodes"
]["start"][1]
assert _bc_center_y > _bc_heel_y + 200, (_bc_center_y, _bc_heel_y)

scissor_posts = _portal_end_posts(scissor_macro, "shed_1-truss-web-1-")
assert len(scissor_posts) >= 2, ("scissor end posts", len(scissor_posts))
assert next(m for m in scissor_macro if m["id"] == "shed_1-truss-post-1-0")[
    "element_type"
] == "truss_chord"

print("PASS: truss types")
print(f"  duo types verified: {', '.join(DUO_TYPES)}")

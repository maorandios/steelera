"""Utilization-based section selection within role-specific candidate pools."""

from __future__ import annotations

import math
from dataclasses import dataclass

from catalog_loader import has_profile, list_profiles
from core.preliminary_loads import PreliminaryLoads
from core.section_props import FY_MPA, SectionProperties, section_properties

GAMMA_M0 = 1.0
GAMMA_M1 = 1.0
MAX_UTILIZATION = 0.90

# Minimum span floors — capacity pick cannot go lighter than these.
_SPAN_CHORD_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "SHS200x200x8"),
    (18_000.0, "SHS150x150x8"),
    (15_000.0, "SHS150x150x6"),
    (12_000.0, "SHS120x120x6"),
]

_SPAN_CHORD_RECOMMENDED_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "SHS200x200x10"),
    (18_000.0, "SHS180x180x10"),
    (15_000.0, "SHS150x150x10"),
    (12_000.0, "SHS120x120x8"),
]

_SPAN_CHORD_CONSERVATIVE_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "SHS250x250x10"),
    (18_000.0, "SHS200x200x10"),
    (15_000.0, "SHS180x180x10"),
    (12_000.0, "SHS150x150x10"),
]

_COLUMN_IPE_CANDIDATES = [
    "IPE200",
    "IPE220",
    "IPE240",
    "IPE270",
    "IPE300",
    "IPE330",
    "IPE360",
    "IPE400",
    "IPE450",
    "IPE500",
]

_COLUMN_SHS_CANDIDATES = [
    "SHS150x150x6",
    "SHS150x150x8",
    "SHS150x150x10",
    "SHS180x180x8",
    "SHS180x180x10",
    "SHS200x200x8",
    "SHS200x200x10",
    "SHS200x200x12.5",
    "SHS250x250x8",
    "SHS250x250x10",
    "SHS250x250x12.5",
    "SHS300x300x10",
    "SHS300x300x12.5",
]

_BRACING_ANGLE_CANDIDATES = [
    "L50x50",
    "L50x50x5",
    "L50x50x6",
    "L60x60x6",
    "L60x60x8",
    "L70x70x6",
    "L70x70x7",
    "L80x80x8",
    "L90x90x9",
    "L100x100x10",
]

_BRACING_CHS_CANDIDATES = [
    "CHS42.4x4",
    "CHS48.3x4",
    "CHS60.3x5",
    "CHS76.1x5",
    "CHS88.9x5",
    "CHS88.9x6.3",
    "CHS114.3x5",
    "CHS114.3x6.3",
    "CHS139.7x6.3",
    "CHS168.3x6.3",
]

_BRACING_SHS_CANDIDATES = [
    "SHS60x60x4",
    "SHS60x60x5",
    "SHS80x80x5",
    "SHS80x80x6",
    "SHS100x100x5",
    "SHS100x100x6",
]

_BRACING_RECOMMENDED_FLOOR: list[tuple[float, str, str]] = [
    # (threshold_mm, dimension, profile) — dimension: height / length / width
    (18_000.0, "height", "L70x70x6"),
    (80_000.0, "length", "L70x70x6"),
    (12_000.0, "height", "L60x60x6"),
    (15_000.0, "width", "L60x60x6"),
    (40_000.0, "length", "L60x60x6"),
    (8_000.0, "height", "L60x60x6"),
]

_BRACING_CONSERVATIVE_FLOOR: list[tuple[float, str, str]] = [
    (18_000.0, "height", "L80x80x8"),
    (80_000.0, "length", "L80x80x8"),
    (12_000.0, "height", "L70x70x6"),
    (15_000.0, "width", "L70x70x6"),
    (40_000.0, "length", "L70x70x6"),
    (8_000.0, "height", "L70x70x7"),
]

# Column tier floors when preliminary util is low — same pattern as bracing/chords.
_COLUMN_RECOMMENDED_FLOOR: list[tuple[float, str, str]] = [
    (22_000.0, "width", "HEA360"),
    (18_000.0, "width", "HEA320"),
    (15_000.0, "width", "HEA300"),
    (12_000.0, "width", "HEA280"),
    (22_000.0, "height", "HEA400"),
    (18_000.0, "height", "HEA360"),
    (15_000.0, "height", "HEA320"),
    (12_000.0, "height", "HEA300"),
    (10_000.0, "height", "HEA280"),
    (8_000.0, "height", "HEA260"),
]

_COLUMN_CONSERVATIVE_FLOOR: list[tuple[float, str, str]] = [
    (22_000.0, "width", "HEA400"),
    (18_000.0, "width", "HEA360"),
    (15_000.0, "width", "HEA320"),
    (12_000.0, "width", "HEA300"),
    (22_000.0, "height", "HEA450"),
    (18_000.0, "height", "HEA400"),
    (15_000.0, "height", "HEA360"),
    (12_000.0, "height", "HEA320"),
    (10_000.0, "height", "HEA300"),
    (8_000.0, "height", "HEA280"),
]

# Max catalog steps above recommended when util governs (prevents HEB1000 jumps).
_MAX_TIER_STEPS_ABOVE_RECOMMENDED = 2

_RAFTER_CANDIDATES = [
    "IPE180",
    "IPE200",
    "IPE220",
    "IPE240",
    "IPE270",
    "IPE300",
    "IPE330",
    "IPE360",
]

_CHORD_SHS_CANDIDATES = [
    "SHS120x120x6",
    "SHS120x120x8",
    "SHS140x140x6",
    "SHS140x140x8",
    "SHS150x150x6",
    "SHS150x150x8",
    "SHS150x150x10",
    "SHS160x160x8",
    "SHS180x180x8",
    "SHS180x180x10",
    "SHS200x200x6",
    "SHS200x200x8",
    "SHS200x200x10",
    "SHS200x200x12.5",
    "SHS250x250x8",
    "SHS250x250x10",
    "SHS250x250x12.5",
]

_WEB_ANGLE_CANDIDATES = [
    "L50x50",
    "L50x50x5",
    "L50x50x6",
    "L60x60x6",
    "L60x60x8",
    "L70x70x6",
    "L70x70x7",
    "L80x80x8",
    "L90x90x9",
]

_WEB_SHS_CANDIDATES = [
    "SHS80x80x5",
    "SHS80x80x6",
    "SHS100x100x5",
    "SHS100x100x6",
    "SHS100x100x8",
    "SHS120x120x6",
    "SHS120x120x8",
    "SHS140x140x6",
    "SHS140x140x8",
    "SHS160x160x8",
    "SHS180x180x8",
]

_WEB_CHS_CANDIDATES = [
    "CHS88.9x5",
    "CHS88.9x6.3",
    "CHS114.3x5",
    "CHS114.3x6.3",
    "CHS139.7x5",
    "CHS139.7x6.3",
    "CHS168.3x6.3",
]

_TIE_BEAM_CANDIDATES = [
    "IPE200",
    "IPE220",
    "IPE240",
    "IPE270",
    "IPE300",
    "IPE330",
    "IPE360",
    "IPE400",
]

_TIE_UTIL_FLOOR_DOMINATED = 0.15

_TIE_RECOMMENDED_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "IPE270"),
    (18_000.0, "IPE240"),
    (15_000.0, "IPE220"),
]

_TIE_CONSERVATIVE_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "IPE300"),
    (18_000.0, "IPE270"),
    (15_000.0, "IPE240"),
]

_SPAN_WEB_FLOOR: list[tuple[float, str]] = [
    (22_000.0, "L70x70x6"),
    (18_000.0, "L60x60x6"),
    (12_000.0, "L50x50x6"),
]

_CHORD_IPE_CANDIDATES = [
    "IPE200",
    "IPE220",
    "IPE240",
    "IPE270",
    "IPE300",
]


@dataclass(frozen=True)
class SelectionResult:
    profile: str
    utilization: float
    governing: str


def _lambda_1() -> float:
    return math.pi * math.sqrt(210_000.0 / FY_MPA)


def _chi_curve_b(slenderness: float) -> float:
    """EC3 buckling curve c (hollow / weak-axis open) — simplified."""
    lam = max(slenderness, 0.01)
    alpha = 0.49
    phi = 0.5 * (1.0 + alpha * (lam - 0.2) + lam**2)
    root = max(phi**2 - lam**2, 0.0)
    return min(1.0, 1.0 / (phi + math.sqrt(root)))


def _chi_curve_a(slenderness: float) -> float:
    """EC3 buckling curve a (strong-axis rolled I) — simplified."""
    lam = max(slenderness, 0.01)
    alpha = 0.21
    phi = 0.5 * (1.0 + alpha * (lam - 0.2) + lam**2)
    root = max(phi**2 - lam**2, 0.0)
    return min(1.0, 1.0 / (phi + math.sqrt(root)))


def _axial_capacity_kn(
    props: SectionProperties,
    length_mm: float,
    *,
    axis: str = "y",
    curve: str = "b",
) -> float:
    r = props.ry_mm if axis == "y" else props.rz_mm
    if r <= 0:
        return 0.0
    slend = (length_mm / r) / _lambda_1()
    chi = _chi_curve_a(slend) if curve == "a" else _chi_curve_b(slend)
    return chi * props.area_mm2 * FY_MPA / (GAMMA_M1 * 1000.0)


def _moment_capacity_knm(
    props: SectionProperties,
    *,
    axis: str = "y",
    ltb_length_mm: float | None = None,
) -> float:
    wpl = props.wpl_y_mm3 if axis == "y" else props.wpl_z_mm3
    m_pl = wpl * FY_MPA / (GAMMA_M0 * 1e6)
    if ltb_length_mm is None or ltb_length_mm <= 0:
        return m_pl
    # Simplified LTB reduction for open I-sections (C_b ≈ 1.0 screening).
    c1 = 1.0
    i = props.iy_mm4
    it = props.area_mm2 * (props.ry_mm**2 + props.rz_mm**2) / max(props.iy_mm4 + props.iz_mm4, 1.0)
    # Approximate torsion constant for open I — use Iz as crude proxy if needed.
    iw = props.iz_mm4 * 0.5
    m_cr = (
        c1
        * math.pi
        * math.sqrt(210_000.0 * i * iw)
        / (ltb_length_mm**2)
        * math.sqrt(props.wpl_y_mm3 / max(i, 1.0))
        / 1e6
    )
    if m_cr <= 0:
        return m_pl
    lam_lt = math.sqrt(m_pl / m_cr)
    chi_lt = 1.0 if lam_lt <= 0.6 else min(1.0, 1.0 / (lam_lt + math.sqrt(lam_lt**2 - 0.36)))
    return min(m_pl, chi_lt * m_pl)


def _is_hollow(props: SectionProperties) -> bool:
    return props.shape in ("RHS", "Box", "CHS") or str(props.shape).upper() == "SHS"


def _column_utilization(
    props: SectionProperties,
    *,
    axial_kn: float,
    moment_knm: float,
    height_mm: float,
) -> tuple[float, str]:
    # Braced frame: 0.7H major, 1.0H minor typical screening.
    if _is_hollow(props):
        n_y = _axial_capacity_kn(props, 0.7 * height_mm, axis="y", curve="b")
        n_z = _axial_capacity_kn(props, 1.0 * height_mm, axis="z", curve="b")
        n_rd = min(n_y, n_z)
        m_rd = props.wpl_y_mm3 * FY_MPA / (GAMMA_M0 * 1e6)
    else:
        n_y = _axial_capacity_kn(props, 0.7 * height_mm, axis="y", curve="a")
        n_z = _axial_capacity_kn(props, 1.0 * height_mm, axis="z", curve="b")
        n_rd = min(n_y, n_z)
        m_rd = _moment_capacity_knm(props, axis="y")
    util_n = axial_kn / n_rd if n_rd > 0 else 99.0
    util_m = moment_knm / m_rd if m_rd > 0 else 99.0
    util = util_n + util_m
    gov = "N+M" if util_n > 0.3 and util_m > 0.3 else ("N" if util_n >= util_m else "M")
    return util, gov


def _rafter_utilization(
    props: SectionProperties,
    *,
    moment_knm: float,
    span_mm: float,
) -> tuple[float, str]:
    # Purlins restrain top flange — unbraced length ~ L/4 screening.
    ltb = max(span_mm / 4.0, 1500.0)
    m_rd = _moment_capacity_knm(props, axis="y", ltb_length_mm=ltb)
    util = moment_knm / m_rd if m_rd > 0 else 99.0
    return util, "M"


def _chord_utilization(
    props: SectionProperties,
    *,
    axial_kn: float,
    panel_length_mm: float,
    prefer_hollow: bool,
) -> tuple[float, str]:
    axis = "y"
    curve = "b" if prefer_hollow else "a"
    n_rd = _axial_capacity_kn(props, panel_length_mm, axis=axis, curve=curve)
    util = axial_kn / n_rd if n_rd > 0 else 99.0
    return util, "N"


def _member_axial_utilization(
    props: SectionProperties,
    *,
    axial_kn: float,
    length_mm: float,
) -> tuple[float, str]:
    """Axial utilization for truss webs (L / SHS / CHS) and tie beams."""
    if props.shape == "Angle":
        n_rd = _axial_capacity_kn(props, length_mm, axis="z", curve="b")
    elif props.shape in ("RHS", "Box", "CHS") or props.shape == "SHS":
        n_rd = _axial_capacity_kn(props, length_mm, axis="y", curve="b")
    else:
        n_rd = _axial_capacity_kn(props, length_mm, axis="y", curve="a")
    util = axial_kn / n_rd if n_rd > 0 else 99.0
    return util, "N"


def _tie_beam_utilization(
    props: SectionProperties,
    *,
    axial_kn: float,
) -> tuple[float, str]:
    """Longitudinal ties work primarily in tension (screening)."""
    n_pl = props.area_mm2 * FY_MPA / (GAMMA_M0 * 1000.0)
    util = axial_kn / n_pl if n_pl > 0 else 99.0
    return util, "N"


def _bracing_utilization(
    props: SectionProperties,
    *,
    axial_kn: float,
) -> tuple[float, str]:
    """X-brace diagonals govern in tension — compression leg often omitted."""
    return _tie_beam_utilization(props, axial_kn=axial_kn)


def _apply_mass_floor(
    pick: SelectionResult,
    floor: str | None,
    *,
    util_fn,
) -> SelectionResult:
    if floor is None or not has_profile(floor):
        return pick
    floor_mass = section_properties(floor).mass_kg_m
    if section_properties(pick.profile).mass_kg_m >= floor_mass - 0.01:
        return pick
    props = section_properties(floor)
    util, gov = util_fn(props)
    return SelectionResult(profile=floor, utilization=round(util, 3), governing=gov)


def _web_candidates(width_mm: float) -> list[str]:
    pool = _available(_WEB_ANGLE_CANDIDATES + _WEB_SHS_CANDIDATES + _WEB_CHS_CANDIDATES)
    pool.sort(key=lambda n: section_properties(n).mass_kg_m)
    floor = _floor_profile(_SPAN_WEB_FLOOR, width_mm)
    if floor:
        floor_mass = section_properties(floor).mass_kg_m
        pool = [c for c in pool if section_properties(c).mass_kg_m >= floor_mass - 0.01]
    return pool


def _available(names: list[str]) -> list[str]:
    return [n for n in names if has_profile(n)]


def _floor_profile(floors: list[tuple[float, str]], width_mm: float) -> str | None:
    for threshold, profile in floors:
        if width_mm >= threshold and has_profile(profile):
            return profile
    return None


def _pick_lightest(
    candidates: list[str],
    *,
    util_fn,
) -> SelectionResult | None:
    best: SelectionResult | None = None
    for name in candidates:
        props = section_properties(name)
        util, gov = util_fn(props)
        if util > MAX_UTILIZATION:
            continue
        if best is None or props.mass_kg_m < section_properties(best.profile).mass_kg_m:
            best = SelectionResult(profile=name, utilization=round(util, 3), governing=gov)
    return best


def _apply_floor(pick: SelectionResult | None, floor: str | None) -> SelectionResult:
    if floor is None:
        if pick is None:
            raise ValueError("No section passed utilization check and no floor defined.")
        return pick
    if pick is None:
        return SelectionResult(profile=floor, utilization=0.0, governing="floor")
    floor_mass = section_properties(floor).mass_kg_m
    pick_mass = section_properties(pick.profile).mass_kg_m
    if pick_mass < floor_mass:
        return SelectionResult(profile=floor, utilization=0.0, governing="floor")
    return pick


def select_column(
    loads: PreliminaryLoads,
    *,
    height_mm: float,
    width_mm: float = 0.0,
    min_profile: str | None = None,
) -> SelectionResult:
    candidates = _column_candidates(
        height_mm=height_mm,
        width_mm=width_mm,
        min_profile=min_profile,
    )

    def util(props: SectionProperties) -> tuple[float, str]:
        return _column_utilization(
            props,
            axial_kn=loads.column_axial_kn,
            moment_knm=loads.column_moment_knm,
            height_mm=height_mm,
        )

    pick = _pick_lightest(candidates, util_fn=util)
    if pick is None and candidates:
        # Heaviest candidate if none pass (shouldn't happen with HEA300+).
        heaviest = candidates[-1]
        u, g = util(section_properties(heaviest))
        pick = SelectionResult(profile=heaviest, utilization=round(u, 3), governing=g)
    return pick or SelectionResult(profile="HEA200", utilization=0.0, governing="default")


def select_rafter(
    loads: PreliminaryLoads,
    *,
    span_mm: float,
) -> SelectionResult:
    candidates = _available(_RAFTER_CANDIDATES)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _rafter_utilization(props, moment_knm=loads.rafter_moment_knm, span_mm=span_mm)

    pick = _pick_lightest(candidates, util_fn=util)
    if pick is None and candidates:
        heaviest = candidates[-1]
        u, g = util(section_properties(heaviest))
        pick = SelectionResult(profile=heaviest, utilization=round(u, 3), governing=g)
    return pick or SelectionResult(profile="IPE200", utilization=0.0, governing="default")


def select_truss_chord(
    loads: PreliminaryLoads,
    *,
    width_mm: float,
    bay_spacing_mm: float,
) -> SelectionResult:
    """Pick SHS chord; compare IPE only when span < 15 m (light truss)."""
    floor = _floor_profile(_SPAN_CHORD_FLOOR, width_mm)
    panel_mm = max(0.85 * bay_spacing_mm, 1200.0)

    shs = _available(_CHORD_SHS_CANDIDATES)
    if floor:
        floor_mass = section_properties(floor).mass_kg_m
        shs = [c for c in shs if section_properties(c).mass_kg_m >= floor_mass - 0.01]

    def shs_util(props: SectionProperties) -> tuple[float, str]:
        return _chord_utilization(
            props,
            axial_kn=loads.chord_axial_kn,
            panel_length_mm=panel_mm,
            prefer_hollow=True,
        )

    shs_pick = _pick_lightest(shs, util_fn=shs_util)

    if width_mm < 15_000:
        ipe = _available(_CHORD_IPE_CANDIDATES)

        def ipe_util(props: SectionProperties) -> tuple[float, str]:
            return _chord_utilization(
                props,
                axial_kn=loads.chord_axial_kn,
                panel_length_mm=panel_mm,
                prefer_hollow=False,
            )

        ipe_pick = _pick_lightest(ipe, util_fn=ipe_util)
        if ipe_pick and shs_pick:
            if section_properties(ipe_pick.profile).mass_kg_m < section_properties(
                shs_pick.profile
            ).mass_kg_m:
                return _apply_floor(ipe_pick, floor)
        elif ipe_pick and not shs_pick:
            return _apply_floor(ipe_pick, floor)

    return _apply_floor(shs_pick, floor)


def _column_candidates(
    *,
    height_mm: float,
    width_mm: float,
    min_profile: str | None = None,
) -> list[str]:
    """HEA / HEB / IPE / SHS column pool — best-shape pick by utilization."""
    names: list[str] = []
    names.extend(_available([str(p["profile_name"]) for p in list_profiles("HEA")]))
    names.extend(_available([str(p["profile_name"]) for p in list_profiles("HEB")]))

    if height_mm < 10_000 and width_mm < 15_000:
        names.extend(_available(_COLUMN_IPE_CANDIDATES))

    if height_mm >= 8_000 or width_mm >= 12_000:
        names.extend(_available(_COLUMN_SHS_CANDIDATES))

    seen: set[str] = set()
    pool: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            pool.append(name)
    pool.sort(key=lambda n: section_properties(n).mass_kg_m)

    if min_profile and has_profile(min_profile):
        min_mass = section_properties(min_profile).mass_kg_m
        pool = [n for n in pool if section_properties(n).mass_kg_m >= min_mass - 0.01]
    return pool


def _all_passing(
    candidates: list[str],
    util_fn,
) -> list[SelectionResult]:
    passing: list[SelectionResult] = []
    for name in candidates:
        props = section_properties(name)
        util, gov = util_fn(props)
        if util <= MAX_UTILIZATION:
            passing.append(
                SelectionResult(profile=name, utilization=round(util, 3), governing=gov)
            )
    passing.sort(key=lambda r: section_properties(r.profile).mass_kg_m)
    return passing


# Preliminary sizing utilization targets (screening, not code design).
_UTIL_LIGHT = 0.82
_UTIL_RECOMMENDED = 0.70
_UTIL_CONSERVATIVE = 0.58
# Below this, tiers step by mass — minimum rules dominate, not util targets.
_COLUMN_UTIL_FLOOR_DOMINATED = 0.45


def _mass(profile: str) -> float:
    return section_properties(profile).mass_kg_m


def _closest_util(
    passing: list[SelectionResult],
    target: float,
    *,
    min_mass: float = 0.0,
) -> SelectionResult:
    pool = [p for p in passing if _mass(p.profile) >= min_mass - 0.01]
    if not pool:
        pool = passing
    return min(pool, key=lambda r: abs(r.utilization - target))


def _tiers_by_step_spread(
    passing: list[SelectionResult],
    *,
    fallback: SelectionResult,
) -> dict[str, SelectionResult]:
    """Spread tiers by catalog steps (not full pool range) when util is floor-dominated."""
    if not passing:
        return {"light": fallback, "recommended": fallback, "conservative": fallback}
    if len(passing) == 1:
        only = passing[0]
        return {"light": only, "recommended": only, "conservative": only}

    light = passing[0]
    recommended = passing[min(1, len(passing) - 1)]
    if recommended.profile == light.profile:
        recommended = _next_heavier_passing(passing, light)
    conservative = _next_heavier_passing(passing, recommended)

    ordered = sorted(
        [light, recommended, conservative],
        key=lambda r: _mass(r.profile),
    )
    if len({r.profile for r in ordered}) >= 2:
        light, recommended, conservative = (
            ordered[0],
            ordered[1] if len(ordered) > 1 else ordered[0],
            ordered[-1],
        )
    return {"light": light, "recommended": recommended, "conservative": conservative}


def _index_in_passing(passing: list[SelectionResult], profile: str) -> int:
    for i, pick in enumerate(passing):
        if pick.profile == profile:
            return i
    masses = [_mass(p.profile) for p in passing]
    target = _mass(profile)
    for i, m in enumerate(masses):
        if m >= target - 0.01:
            return i
    return len(passing) - 1


def _cap_conservative_steps(
    tiers: dict[str, SelectionResult],
    passing: list[SelectionResult],
    *,
    max_steps: int = _MAX_TIER_STEPS_ABOVE_RECOMMENDED,
) -> dict[str, SelectionResult]:
    """Keep conservative within a few catalog steps of recommended."""
    if not passing:
        return tiers
    rec_idx = _index_in_passing(passing, tiers["recommended"].profile)
    cap_idx = min(rec_idx + max_steps, len(passing) - 1)
    capped = passing[cap_idx]
    if _mass(capped.profile) < _mass(tiers["conservative"].profile):
        tiers = dict(tiers)
        tiers["conservative"] = capped
    return tiers


def _tiers_from_passing_util_targets(
    passing: list[SelectionResult],
    *,
    fallback: SelectionResult,
) -> dict[str, SelectionResult]:
    """Map tiers to utilization targets when demand governs sizing."""
    if not passing:
        return {"light": fallback, "recommended": fallback, "conservative": fallback}

    light = _closest_util(passing, _UTIL_LIGHT)
    recommended = _closest_util(
        passing,
        _UTIL_RECOMMENDED,
        min_mass=_mass(light.profile) + 0.02,
    )
    if recommended.profile == light.profile and len(passing) > 1:
        heavier = [p for p in passing if _mass(p.profile) > _mass(light.profile) + 0.01]
        if heavier:
            recommended = _closest_util(heavier, _UTIL_RECOMMENDED)
    conservative = _closest_util(
        passing,
        _UTIL_CONSERVATIVE,
        min_mass=_mass(recommended.profile) + 0.02,
    )
    if conservative.profile == recommended.profile and len(passing) > 1:
        heavier = [p for p in passing if _mass(p.profile) > _mass(recommended.profile) + 0.01]
        if heavier:
            conservative = _closest_util(heavier, _UTIL_CONSERVATIVE)

    # Guarantee non-decreasing mass across tiers.
    ordered = sorted(
        [light, recommended, conservative],
        key=lambda r: _mass(r.profile),
    )
    if len({r.profile for r in ordered}) >= 2:
        light, recommended, conservative = (
            ordered[0],
            ordered[1] if len(ordered) > 1 else ordered[0],
            ordered[-1],
        )

    return {"light": light, "recommended": recommended, "conservative": conservative}


def _tiers_from_passing(
    passing: list[SelectionResult],
    *,
    height_mm: float,
    fallback: SelectionResult,
) -> dict[str, SelectionResult]:
    """Map light / recommended / conservative to utilization or mass spread."""
    del height_mm  # height affects min floor only, not tier index bumps
    if not passing:
        return {"light": fallback, "recommended": fallback, "conservative": fallback}

    if max(p.utilization for p in passing) < _COLUMN_UTIL_FLOOR_DOMINATED:
        return _tiers_by_step_spread(passing, fallback=fallback)

    tiers = _tiers_from_passing_util_targets(passing, fallback=fallback)
    return _cap_conservative_steps(tiers, passing)


def _next_heavier_passing(
    passing: list[SelectionResult],
    pick: SelectionResult,
) -> SelectionResult:
    heavier = [p for p in passing if _mass(p.profile) > _mass(pick.profile) + 0.01]
    return heavier[0] if heavier else pick


def _dimension_floor(
    floors: list[tuple[float, str, str]],
    *,
    height_mm: float,
    length_mm: float = 0.0,
    width_mm: float = 0.0,
) -> str | None:
    best: tuple[float, str] | None = None
    dims = {"height": height_mm, "length": length_mm, "width": width_mm}
    for threshold, dim, profile in floors:
        val = dims.get(dim, 0.0)
        if val >= threshold and (best is None or threshold > best[0]):
            best = (threshold, profile)
    return best[1] if best else None


def _tiers_floor_anchored(
    passing: list[SelectionResult],
    *,
    fallback: SelectionResult,
    rec_floor: str | None,
    con_floor: str | None,
    util_fn,
) -> dict[str, SelectionResult]:
    """Tier picks from geometry floors when utilization does not govern."""
    if not passing:
        return {"light": fallback, "recommended": fallback, "conservative": fallback}

    light = passing[0]
    recommended = _apply_mass_floor(light, rec_floor, util_fn=util_fn)
    if recommended.profile == light.profile:
        recommended = _next_heavier_passing(passing, light)

    conservative = _apply_mass_floor(recommended, con_floor, util_fn=util_fn)
    if conservative.profile == recommended.profile:
        conservative = _next_heavier_passing(passing, recommended)

    ordered = sorted(
        [light, recommended, conservative],
        key=lambda r: _mass(r.profile),
    )
    if len({r.profile for r in ordered}) >= 2:
        light, recommended, conservative = (
            ordered[0],
            ordered[1] if len(ordered) > 1 else ordered[0],
            ordered[-1],
        )
    return {"light": light, "recommended": recommended, "conservative": conservative}


def select_column_tiers(
    loads: PreliminaryLoads,
    *,
    height_mm: float,
    width_mm: float = 0.0,
    min_profile: str | None = None,
) -> dict[str, SelectionResult]:
    candidates = _column_candidates(
        height_mm=height_mm,
        width_mm=width_mm,
        min_profile=min_profile,
    )

    def util(props: SectionProperties) -> tuple[float, str]:
        return _column_utilization(
            props,
            axial_kn=loads.column_axial_kn,
            moment_knm=loads.column_moment_knm,
            height_mm=height_mm,
        )

    passing = _all_passing(candidates, util)
    fallback = select_column(
        loads,
        height_mm=height_mm,
        width_mm=width_mm,
        min_profile=min_profile,
    )
    rec_floor = _dimension_floor(
        _COLUMN_RECOMMENDED_FLOOR,
        height_mm=height_mm,
        width_mm=width_mm,
    )
    con_floor = _dimension_floor(
        _COLUMN_CONSERVATIVE_FLOOR,
        height_mm=height_mm,
        width_mm=width_mm,
    )
    if passing and max(p.utilization for p in passing) < _COLUMN_UTIL_FLOOR_DOMINATED:
        tiers = _tiers_floor_anchored(
            passing,
            fallback=fallback,
            rec_floor=rec_floor,
            con_floor=con_floor,
            util_fn=util,
        )
        if min_profile:
            tiers["light"] = _apply_mass_floor(
                tiers["light"], min_profile, util_fn=util
            )
            tiers["recommended"] = _apply_mass_floor(
                tiers["recommended"], min_profile, util_fn=util
            )
            tiers["conservative"] = _apply_mass_floor(
                tiers["conservative"], min_profile, util_fn=util
            )
        return tiers

    tiers = _tiers_from_passing_util_targets(passing, fallback=fallback)
    tier_floors = {"light": min_profile, "recommended": rec_floor, "conservative": con_floor}
    for key in tiers:
        tiers[key] = _apply_mass_floor(tiers[key], tier_floors.get(key), util_fn=util)
    return _cap_conservative_steps(tiers, passing)


def select_truss_chord_tiers(
    loads: PreliminaryLoads,
    *,
    width_mm: float,
    bay_spacing_mm: float,
) -> dict[str, SelectionResult]:
    floor = _floor_profile(_SPAN_CHORD_FLOOR, width_mm)
    panel_mm = max(0.85 * bay_spacing_mm, 1200.0)
    shs = _available(_CHORD_SHS_CANDIDATES)
    if floor:
        floor_mass = section_properties(floor).mass_kg_m
        shs = [c for c in shs if section_properties(c).mass_kg_m >= floor_mass - 0.01]

    def util(props: SectionProperties) -> tuple[float, str]:
        return _chord_utilization(
            props,
            axial_kn=loads.chord_axial_kn,
            panel_length_mm=panel_mm,
            prefer_hollow=True,
        )

    passing = _all_passing(shs, util)
    fallback = select_truss_chord(loads, width_mm=width_mm, bay_spacing_mm=bay_spacing_mm)
    tiers = _tiers_from_passing(passing, height_mm=0.0, fallback=fallback)
    tier_floors = {
        "light": _floor_profile(_SPAN_CHORD_FLOOR, width_mm),
        "recommended": _floor_profile(_SPAN_CHORD_RECOMMENDED_FLOOR, width_mm),
        "conservative": _floor_profile(_SPAN_CHORD_CONSERVATIVE_FLOOR, width_mm),
    }
    for key in tiers:
        tiers[key] = _apply_mass_floor(tiers[key], tier_floors.get(key), util_fn=util)
    return _cap_conservative_steps(tiers, passing)


def _bracing_candidates(
    *,
    height_mm: float,
    length_mm: float,
) -> list[str]:
    """L / CHS / SHS bracing pool — best-shape pick by utilization."""
    names: list[str] = []
    names.extend(_available(_BRACING_ANGLE_CANDIDATES))
    names.extend(_available(_BRACING_CHS_CANDIDATES))

    if height_mm >= 10_000 or length_mm >= 50_000:
        names.extend(_available(_BRACING_SHS_CANDIDATES))

    seen: set[str] = set()
    pool: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            pool.append(name)
    pool.sort(key=lambda n: section_properties(n).mass_kg_m)
    return pool


def select_bracing_member(
    loads: PreliminaryLoads,
    *,
    height_mm: float,
    length_mm: float,
) -> SelectionResult:
    candidates = _bracing_candidates(height_mm=height_mm, length_mm=length_mm)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _bracing_utilization(props, axial_kn=loads.bracing_axial_kn)

    pick = _pick_lightest(candidates, util_fn=util)
    if pick is None and candidates:
        heaviest = candidates[-1]
        u, g = util(section_properties(heaviest))
        pick = SelectionResult(profile=heaviest, utilization=round(u, 3), governing=g)
    return pick or SelectionResult(profile="L50x50", utilization=0.0, governing="default")


def select_bracing_tiers(
    loads: PreliminaryLoads,
    *,
    height_mm: float,
    length_mm: float,
    width_mm: float = 0.0,
) -> dict[str, SelectionResult]:
    """Utilization-based bracing picks from L / CHS / SHS candidates."""
    candidates = _bracing_candidates(height_mm=height_mm, length_mm=length_mm)
    def util(props: SectionProperties) -> tuple[float, str]:
        return _bracing_utilization(props, axial_kn=loads.bracing_axial_kn)

    passing = _all_passing(candidates, util)
    fallback = select_bracing_member(
        loads,
        height_mm=height_mm,
        length_mm=length_mm,
    )
    rec_floor = _dimension_floor(
        _BRACING_RECOMMENDED_FLOOR,
        height_mm=height_mm,
        length_mm=length_mm,
        width_mm=width_mm,
    )
    con_floor = _dimension_floor(
        _BRACING_CONSERVATIVE_FLOOR,
        height_mm=height_mm,
        length_mm=length_mm,
        width_mm=width_mm,
    )

    if passing and max(p.utilization for p in passing) < _COLUMN_UTIL_FLOOR_DOMINATED:
        return _tiers_floor_anchored(
            passing,
            fallback=fallback,
            rec_floor=rec_floor,
            con_floor=con_floor,
            util_fn=util,
        )

    tiers = _tiers_from_passing_util_targets(passing, fallback=fallback)
    tier_floors = {"light": None, "recommended": rec_floor, "conservative": con_floor}
    for key in tiers:
        tiers[key] = _apply_mass_floor(tiers[key], tier_floors.get(key), util_fn=util)
    return tiers


def select_web_tiers(
    loads: PreliminaryLoads,
    *,
    width_mm: float,
) -> dict[str, SelectionResult]:
    """Utilization-based web picks from L / SHS / CHS candidates."""
    candidates = _web_candidates(width_mm)
    length_mm = max(loads.web_length_mm, 800.0)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _member_axial_utilization(
            props,
            axial_kn=loads.web_axial_kn,
            length_mm=length_mm,
        )

    passing = _all_passing(candidates, util)
    fallback = select_web_member(loads, width_mm=width_mm)
    return _tiers_from_passing(passing, height_mm=0.0, fallback=fallback)


def select_web_member(
    loads: PreliminaryLoads,
    *,
    width_mm: float,
) -> SelectionResult:
    candidates = _web_candidates(width_mm)
    length_mm = max(loads.web_length_mm, 800.0)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _member_axial_utilization(
            props,
            axial_kn=loads.web_axial_kn,
            length_mm=length_mm,
        )

    pick = _pick_lightest(candidates, util_fn=util)
    if pick is None and candidates:
        heaviest = candidates[-1]
        u, g = util(section_properties(heaviest))
        pick = SelectionResult(profile=heaviest, utilization=round(u, 3), governing=g)
    return pick or SelectionResult(profile="L50x50", utilization=0.0, governing="default")


def select_tie_beam_tiers(
    loads: PreliminaryLoads,
    *,
    width_mm: float = 0.0,
) -> dict[str, SelectionResult]:
    candidates = _available(_TIE_BEAM_CANDIDATES)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _tie_beam_utilization(props, axial_kn=loads.tie_beam_axial_kn)

    passing = _all_passing(candidates, util)
    fallback = select_tie_beam(loads)
    rec_floor = _floor_profile(_TIE_RECOMMENDED_FLOOR, width_mm)
    con_floor = _floor_profile(_TIE_CONSERVATIVE_FLOOR, width_mm)

    if passing and max(p.utilization for p in passing) < _TIE_UTIL_FLOOR_DOMINATED:
        return _tiers_floor_anchored(
            passing,
            fallback=fallback,
            rec_floor=rec_floor,
            con_floor=con_floor,
            util_fn=util,
        )

    tiers = _tiers_from_passing_util_targets(passing, fallback=fallback)
    tier_floors = {"light": None, "recommended": rec_floor, "conservative": con_floor}
    for key in tiers:
        tiers[key] = _apply_mass_floor(tiers[key], tier_floors.get(key), util_fn=util)
    return tiers


def select_tie_beam(loads: PreliminaryLoads) -> SelectionResult:
    candidates = _available(_TIE_BEAM_CANDIDATES)

    def util(props: SectionProperties) -> tuple[float, str]:
        return _tie_beam_utilization(props, axial_kn=loads.tie_beam_axial_kn)

    pick = _pick_lightest(candidates, util_fn=util)
    if pick is None and candidates:
        heaviest = candidates[-1]
        u, g = util(section_properties(heaviest))
        pick = SelectionResult(profile=heaviest, utilization=round(u, 3), governing=g)
    return pick or SelectionResult(profile="IPE200", utilization=0.0, governing="default")

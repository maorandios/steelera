"""Conservative structural recommendations from site context + geometry."""



from __future__ import annotations



from catalog_loader import has_profile

from core.preliminary_loads import estimate_preliminary_loads

from core.section_selector import (

    select_bracing_tiers,

    select_column,

    select_column_tiers,

    select_truss_chord,

    select_truss_chord_tiers,

    select_tie_beam_tiers,

    select_web_tiers,

)

from schemas.site import SiteContext, StructuralRecommendations



# Global preliminary-design safety margins (all regions).

GLOBAL_LOAD_FLOOR = 8.5

GLOBAL_CONSERVATISM_FACTOR = 1.10

MIN_DESIGN_WIND_MS_FOR_SIZING = 7.5



_TRUSS_WIDTH_THRESHOLD_MM = 15_000.0

_LARGE_SPAN_MM = 15_000.0

_LARGE_LENGTH_MM = 40_000.0

_MIN_EAVE_FOR_BUMP_MM = 6_000.0

_TALL_EAVE_MM = 10_000.0

_VERY_TALL_EAVE_MM = 12_000.0



_COLUMN_TIERS = [

    "HEA200",

    "HEA220",

    "HEA240",

    "HEA260",

    "HEA280",

    "HEA300",

    "HEA320",

    "HEA360",

    "HEA400",

]





def _effective_load(site: SiteContext) -> float:

    """Sizing load index — conservative floor without changing displayed site data."""

    terrain_factor = {"0": 1.25, "II": 1.12, "III": 1.0, "IV": 0.92}.get(

        site.terrain_class,

        1.0,

    )

    floored_design = max(site.design_wind_proxy_ms, MIN_DESIGN_WIND_MS_FOR_SIZING)

    from_floored_wind = floored_design * terrain_factor

    return round(

        max(

            site.load_index * GLOBAL_CONSERVATISM_FACTOR,

            from_floored_wind * 0.98,

            GLOBAL_LOAD_FLOOR,

        ),

        2,

    )





def _column_tier_for_height(height_mm: float) -> int:

    if height_mm >= _VERY_TALL_EAVE_MM:

        return 5

    if height_mm >= _TALL_EAVE_MM:

        return 4

    if height_mm >= 7_000:

        return 3

    if height_mm >= 5_500:

        return 2

    if height_mm >= 4_500:

        return 1

    return 0





def _bump_column_tier(base: int, bumps: int) -> int:

    return min(len(_COLUMN_TIERS) - 1, base + bumps)





def _minimum_column_profile(

    *,

    width_mm: float,

    height_mm: float,

    load: float,

) -> str:

    """Conservative tier floor before capacity-based pick."""

    col_base = _column_tier_for_height(height_mm)

    col_bumps = 0

    if width_mm >= 12_000 or height_mm >= _MIN_EAVE_FOR_BUMP_MM:

        col_bumps += 1

    if load >= 9.0:

        col_bumps += 1

    if load >= 11.5:

        col_bumps += 1

    if width_mm >= 18_000:

        col_bumps += 1

    if width_mm >= 22_000:

        col_bumps += 1

    if height_mm >= 7_000 and load >= 10.0:

        col_bumps += 1

    if height_mm >= _TALL_EAVE_MM:

        col_bumps += 1

    if height_mm >= _VERY_TALL_EAVE_MM:

        col_bumps += 1

    return _COLUMN_TIERS[_bump_column_tier(col_base, col_bumps)]





def _truss_web_profile(loads, *, width_mm: float) -> str:
    return select_web_tiers(loads, width_mm=width_mm)["recommended"].profile





def compute_structural_recommendations(

    *,

    width_mm: float,

    length_mm: float,

    height_mm: float,

    roof_pitch_deg: float,

    site: SiteContext,

    bay_spacing_override_mm: float | None = None,

    roof_style: str = "duo_pitch",

) -> StructuralRecommendations:

    """Deterministic truss/column/bay/bracing picks from site + geometry."""

    load = _effective_load(site)

    width = float(width_mm)

    length = float(length_mm)

    height = float(height_mm)



    use_truss = width >= _TRUSS_WIDTH_THRESHOLD_MM or (

        width >= 12_000 and load >= 10.5

    )

    truss_type = "pratt" if use_truss else "none"



    if bay_spacing_override_mm and bay_spacing_override_mm > 0:

        bay_mm = float(bay_spacing_override_mm)

    elif width >= _LARGE_SPAN_MM or length >= _LARGE_LENGTH_MM or load >= 8.5:

        bay_mm = 6_000.0

    else:

        bay_mm = 7_500.0

    bay_mm = max(3_000.0, min(bay_mm, 8_000.0))



    loads = estimate_preliminary_loads(

        width_mm=width,

        length_mm=length,

        height_mm=height,

        roof_pitch_deg=roof_pitch_deg,

        bay_spacing_mm=bay_mm,

        effective_load_index=load,

        site=site,

        roof_style=roof_style,

    )



    min_column = _minimum_column_profile(width_mm=width, height_mm=height, load=load)

    column_profile = select_column(

        loads,

        height_mm=height,

        width_mm=width,

        min_profile=min_column,

    ).profile



    is_open = site.exposure == "open" or site.terrain_class in ("0", "II")

    x_bracing = True

    roof_bracing = (

        load >= 7.5

        or bay_mm >= 6_500

        or width >= _LARGE_SPAN_MM

        or is_open

    )

    gable_bracing = is_open or width >= _LARGE_SPAN_MM

    sag_rods = use_truss and (width >= 12_000 or load >= 8.5 or bay_mm >= 6_000)

    fly_braces = load >= 12.0 and not use_truss

    haunches = not use_truss and width >= 12_000 and load >= 9.5



    chord = (

        select_truss_chord(loads, width_mm=width, bay_spacing_mm=bay_mm).profile

        if use_truss

        else None

    )

    web = _truss_web_profile(loads, width_mm=width) if use_truss else None



    return StructuralRecommendations(

        bay_spacing_mm=bay_mm,

        use_truss=use_truss,

        truss_type=truss_type,

        column_profile=column_profile,

        truss_chord_profile=chord,

        truss_web_profile=web,

        x_bracing=x_bracing,

        roof_bracing=roof_bracing,

        gable_bracing=gable_bracing,

        sag_rods=sag_rods,

        fly_braces=fly_braces,

        haunches=haunches,

    )





def compute_section_tier_options(

    *,

    width_mm: float,

    length_mm: float,

    height_mm: float,

    roof_pitch_deg: float,

    site: SiteContext,

    bay_spacing_mm: float,

    use_truss: bool,

    load: float | None = None,

    roof_style: str = "duo_pitch",

) -> dict[str, dict[str, str | float | None]]:

    """Light / recommended / conservative section packages (Python-validated)."""

    effective_load = load if load is not None else _effective_load(site)

    loads = estimate_preliminary_loads(

        width_mm=width_mm,

        length_mm=length_mm,

        height_mm=height_mm,

        roof_pitch_deg=roof_pitch_deg,

        bay_spacing_mm=bay_spacing_mm,

        effective_load_index=effective_load,

        site=site,

        roof_style=roof_style,

    )

    min_column = _minimum_column_profile(

        width_mm=width_mm,

        height_mm=height_mm,

        load=effective_load,

    )

    col_tiers = select_column_tiers(

        loads,

        height_mm=height_mm,

        width_mm=width_mm,

        min_profile=min_column,

    )

    brace_tiers = select_bracing_tiers(

        loads,

        height_mm=height_mm,

        length_mm=length_mm,

        width_mm=width_mm,

    )

    web_tiers = select_web_tiers(loads, width_mm=width_mm) if use_truss else {}
    tie_tiers = select_tie_beam_tiers(loads, width_mm=width_mm)
    chord_tiers = (
        select_truss_chord_tiers(
            loads, width_mm=width_mm, bay_spacing_mm=bay_spacing_mm
        )
        if use_truss
        else {}
    )

    packages: dict[str, dict[str, str | float | None]] = {}

    for tier in ("light", "recommended", "conservative"):

        chord_profile = None
        chord_util = None
        if use_truss:
            chord_sel = chord_tiers[tier]
            chord_profile = chord_sel.profile
            chord_util = chord_sel.utilization

        web_sel = web_tiers.get(tier) if use_truss else None
        tie_sel = tie_tiers[tier]
        col_sel = col_tiers[tier]

        brace_sel = brace_tiers[tier]

        packages[tier] = {
            "tier": tier,
            "column_profile": col_sel.profile,
            "column_utilization": col_sel.utilization,
            "truss_chord_profile": chord_profile,
            "chord_utilization": chord_util,
            "truss_web_profile": web_sel.profile if web_sel else None,
            "web_utilization": web_sel.utilization if web_sel else None,
            "tie_beam_profile": tie_sel.profile,
            "tie_beam_utilization": tie_sel.utilization,
            "bracing_profile": brace_sel.profile,
            "bracing_utilization": brace_sel.utilization,
        }

    return packages



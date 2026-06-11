"""Map sketch intent to utilization-based section tiers."""

from __future__ import annotations

import math

from core.preliminary_loads import estimate_preliminary_loads
from core.section_selector import SelectionResult, select_bracing_tiers, select_tie_beam_tiers
from core.shed_params import DEFAULT_SHED_PARAMS, infer_shed_params_from_elements
from core.shed_proposal import _default_site_context
from schemas.elements import ProjectElementMm
from schemas.site import SiteContext
from schemas.sketch import SketchProfileOption, SketchSnapNode, StructuralIntentKind

_TIER_LABELS = {
    "light": "Light",
    "recommended": "Optimal",
    "conservative": "Conservative",
}

_DISPLAY_ORDER = ("recommended", "light", "conservative")

_PURLIN_TIERS: list[tuple[float, tuple[str, str, str]]] = [
    (
        6000.0,
        ("Z200x1.5", "Z200x2", "Z200x2.5"),
    ),
    (
        9000.0,
        ("Z200x2", "Z250x2", "Z250x2.5"),
    ),
    (
        float("inf"),
        ("Z250x2", "Z250x2.5", "Z250x3"),
    ),
]


def _shed_dims(
    elements: list[ProjectElementMm],
    shed_params: dict | None,
) -> tuple[float, float, float, float, float, str]:
    params = dict(DEFAULT_SHED_PARAMS)
    if shed_params:
        params.update(shed_params)
    elif elements:
        inferred = infer_shed_params_from_elements(elements)
        params.update(inferred)

    width = float(params.get("width", 12000.0))
    length = float(params.get("length", 30000.0))
    height = float(params.get("height", 6000.0))
    pitch = float(params.get("roof_pitch_deg", 10.0))
    roof_style = str(params.get("roof_style", "duo_pitch"))
    x_spans = params.get("x_spans") or [width]
    bay = float(x_spans[0]) if x_spans else 6000.0
    return width, length, height, pitch, bay, roof_style


def _tier_options(tiers: dict[str, SelectionResult]) -> list[SketchProfileOption]:
    out: list[SketchProfileOption] = []
    for key in _DISPLAY_ORDER:
        pick = tiers.get(key)
        if pick is None:
            continue
        out.append(
            SketchProfileOption(
                profile=pick.profile,
                tier=key,  # type: ignore[arg-type]
                tier_label=_TIER_LABELS[key],
                utilization=pick.utilization,
                governing=pick.governing,
            )
        )
    return out


def _purlin_options(span_mm: float) -> list[SketchProfileOption]:
    for limit, (light, rec, con) in _PURLIN_TIERS:
        if span_mm < limit:
            return [
                SketchProfileOption(
                    profile=rec,
                    tier="recommended",
                    tier_label=_TIER_LABELS["recommended"],
                    utilization=0.0,
                    governing="span_rule",
                ),
                SketchProfileOption(
                    profile=light,
                    tier="light",
                    tier_label=_TIER_LABELS["light"],
                    utilization=0.0,
                    governing="span_rule",
                ),
                SketchProfileOption(
                    profile=con,
                    tier="conservative",
                    tier_label=_TIER_LABELS["conservative"],
                    utilization=0.0,
                    governing="span_rule",
                ),
            ]
    return []


def recommend_sketch_profiles(
    kind: StructuralIntentKind,
    *,
    elements: list[ProjectElementMm],
    start: SketchSnapNode,
    end: SketchSnapNode,
    span_mm: float,
    shed_params: dict | None = None,
    site_context: SiteContext | None = None,
) -> list[SketchProfileOption]:
    site = site_context or _default_site_context()
    width, length, height, pitch, bay, roof_style = _shed_dims(elements, shed_params)
    loads = estimate_preliminary_loads(
        width_mm=width,
        length_mm=length,
        height_mm=height,
        roof_pitch_deg=pitch,
        bay_spacing_mm=bay,
        effective_load_index=site.load_index,
        site=site,
        roof_style=roof_style,
    )

    if kind in ("tie_beam", "beam", "unknown"):
        return _tier_options(select_tie_beam_tiers(loads, width_mm=width))

    if kind == "bracing":
        brace_height = max(abs(end.y - start.y), height * 0.5, 2000.0)
        return _tier_options(
            select_bracing_tiers(
                loads,
                height_mm=brace_height,
                length_mm=max(span_mm, loads.bracing_length_mm),
                width_mm=width,
            )
        )

    if kind == "purlin":
        return _purlin_options(span_mm)

    return _tier_options(select_tie_beam_tiers(loads, width_mm=width))

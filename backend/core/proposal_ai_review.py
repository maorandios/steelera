"""AI review of Python-validated section tier packages."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from openai import OpenAI

from core.env_loader import load_env
from core.preliminary_loads import PreliminaryLoads
from schemas.proposal import AiProposalReview, SectionTierPackage
from schemas.site import SiteContext

load_env()

MODEL = "gpt-4o-mini"
TierName = Literal["light", "recommended", "conservative"]


def _client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _tier_line(t: SectionTierPackage) -> str:
    util = (
        f" (col util {t.column_utilization:.2f})"
        if t.column_utilization is not None
        else ""
    )
    return f"{t.column_profile}{util}"


def _comparison_summary(tiers: list[SectionTierPackage]) -> str:
    by = {t.tier: t for t in tiers}
    return (
        f"Light: {_tier_line(by['light'])} · "
        f"Recommended: {_tier_line(by['recommended'])} · "
        f"Conservative: {_tier_line(by['conservative'])}."
    )


def _fallback_review(
    tiers: list[SectionTierPackage],
    warnings: list[str],
) -> AiProposalReview:
    rec = next((t for t in tiers if t.tier == "recommended"), tiers[0])
    return AiProposalReview(
        narrative=(
            "Python generated three preliminary packages. The recommended package "
            f"({rec.column_profile} columns) is pre-selected — column utilization is "
            "within the target preliminary range; review all members before building."
        ),
        recommended_tier="recommended",
        comparison_summary=_comparison_summary(tiers),
        concerns=warnings,
        ai_available=False,
    )


def review_proposal_with_ai(
    *,
    summary: str,
    site: SiteContext,
    width_m: float,
    length_m: float,
    height_m: float,
    use_truss: bool,
    loads: PreliminaryLoads,
    tiers: list[SectionTierPackage],
    warnings: list[str],
) -> AiProposalReview:
    """Compare Python tier packages and recommend one (validated options only)."""
    client = _client()
    if client is None:
        return _fallback_review(tiers, warnings)

    tier_payload = [t.model_dump() for t in tiers]
    system = (
        "You are a structural engineering reviewer for Steelera preliminary shed proposals. "
        "Python has computed three VALIDATED section packages with target utilizations: "
        "light (~0.82), recommended (~0.70), conservative (~0.58) for COLUMNS. "
        "Always set recommended_tier to 'recommended' — Python pre-selects that package. "
        "Your job is to EXPLAIN tradeoffs using column_utilization values. "
        "Say columns are 'within the target preliminary range' — never 'acceptable limits', "
        "'code compliant', or 'within design limits'. "
        "Chord utilization below 0.15 is NOT reliable — chords use span minimum floors; "
        "if chord_utilization is very low, say the truss force model is simplified and "
        "do not praise chord sizing. "
        "If recommended column utilization is below 0.55, note it may be heavier than needed. "
        "If light column utilization is above 0.88, note stability review is needed. "
        "Repeat python_warnings concerns that mention farm height or chord utilization. "
        "Do NOT invent profile sizes outside the packages. "
        "Keep narrative under 3 sentences. This is NOT code-compliant design."
    )
    user_content = json.dumps(
        {
            "summary": summary,
            "site": {
                "location": site.location_label,
                "mean_wind_ms": site.mean_wind_ms,
                "exposure_proxy_ms": site.design_wind_proxy_ms,
                "terrain": site.terrain_class,
                "exposure": site.exposure,
                "load_index": site.load_index,
            },
            "geometry_m": {"width": width_m, "length": length_m, "height": height_m},
            "use_truss": use_truss,
            "estimated_loads": {
                "roof_pressure_kn_m2": loads.roof_pressure_kn_m2,
                "column_moment_knm": loads.column_moment_knm,
                "chord_axial_kn": loads.chord_axial_kn,
            },
            "python_tier_packages": tier_payload,
            "python_warnings": warnings,
        },
        indent=2,
    )

    schema = {
        "type": "object",
        "properties": {
            "narrative": {"type": "string"},
            "recommended_tier": {
                "type": "string",
                "enum": ["light", "recommended", "conservative"],
            },
            "comparison_summary": {"type": "string"},
            "concerns": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "narrative",
            "recommended_tier",
            "comparison_summary",
            "concerns",
        ],
        "additionalProperties": False,
    }

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "proposal_review",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0.2,
        )
        raw: dict[str, Any] = json.loads(resp.choices[0].message.content or "{}")
        return AiProposalReview(
            narrative=str(raw.get("narrative", "")),
            recommended_tier="recommended",
            comparison_summary=str(raw.get("comparison_summary", ""))
            or _comparison_summary(tiers),
            concerns=list(raw.get("concerns") or warnings),
            ai_available=True,
        )
    except Exception:
        return _fallback_review(tiers, warnings)

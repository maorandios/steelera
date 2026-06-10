"""Deterministic engineering proposal from wizard inputs (Python owns the numbers)."""

from __future__ import annotations

from core.load_engine import (
    _effective_load,
    compute_section_tier_options,
    compute_structural_recommendations,
)
from core.preliminary_loads import estimate_preliminary_loads
from core.proposal_ai_review import review_proposal_with_ai
from core.proposal_copy import build_proposal_rationale
from core.proposal_validator import validate_section_package
from core.proposal_warnings import (
    build_proposal_warnings,
    chord_utilization_warnings,
    column_alternatives_note,
    column_utilization_warnings,
    minimum_rules_summary_warning,
    tie_utilization_warnings,
)
from core.site_context import resolve_site_context
from schemas.proposal import (
    AiProposalReview,
    SectionTierPackage,
    ShedProposalRequest,
    ShedProposalResponse,
    TierLiteral,
)
from schemas.site import SiteContext, StructuralRecommendations
from schemas.spatial_grid import GridDefinition

_DEFAULT_BAY_MM = 6_000.0


def _default_site_context() -> SiteContext:
    return SiteContext(
        latitude=0.0,
        longitude=0.0,
        location_label="",
        mean_wind_ms=6.0,
        design_wind_proxy_ms=8.5,
        terrain_class="III",
        exposure="open",
        load_index=8.5,
        data_sources=["default"],
    )


def _z_spans_for_length(length_mm: float, bay_spacing_mm: float | None) -> list[float]:
    spacing = float(bay_spacing_mm or _DEFAULT_BAY_MM)
    if spacing <= 0:
        spacing = _DEFAULT_BAY_MM
    n_bays = max(1, round(length_mm / spacing))
    actual_spacing = length_mm / n_bays
    return [round(actual_spacing, 3) for _ in range(n_bays)]


def _resolve_site(request: ShedProposalRequest) -> SiteContext:
    if request.latitude is not None and request.longitude is not None:
        return resolve_site_context(
            request.latitude,
            request.longitude,
            location_label=request.location_label,
            surroundings=request.site_surroundings,
        )
    return _default_site_context()


def _terrain_label(terrain: str) -> str:
    labels = {
        "0": "coastal / open (Cat 0)",
        "II": "open terrain (Cat II)",
        "III": "suburban (Cat III)",
        "IV": "urban (Cat IV)",
    }
    return labels.get(terrain, terrain)


def _apply_tier_to_grid(
    gd: GridDefinition,
    rec: StructuralRecommendations,
    tier_pkg: SectionTierPackage,
) -> GridDefinition:
    return gd.model_copy(
        update={
            "column_profile": tier_pkg.column_profile,
            "bracing_profile": tier_pkg.bracing_profile,
            "truss_chord_profile": tier_pkg.truss_chord_profile
            if rec.use_truss
            else None,
            "truss_web_profile": tier_pkg.truss_web_profile if rec.use_truss else None,
            "tie_beam_profile": tier_pkg.tie_beam_profile,
        }
    )


def _tier_packages_from_options(
    options: dict[str, dict[str, str | float | None]],
) -> list[SectionTierPackage]:
    order: list[TierLiteral] = ["light", "recommended", "conservative"]
    return [
        SectionTierPackage(
            tier=tier,
            column_profile=str(options[tier]["column_profile"]),
            column_utilization=float(options[tier]["column_utilization"])
            if options[tier].get("column_utilization") is not None
            else None,
            truss_chord_profile=(
                str(options[tier]["truss_chord_profile"])
                if options[tier].get("truss_chord_profile")
                else None
            ),
            chord_utilization=float(options[tier]["chord_utilization"])
            if options[tier].get("chord_utilization") is not None
            else None,
            truss_web_profile=(
                str(options[tier]["truss_web_profile"])
                if options[tier].get("truss_web_profile")
                else None
            ),
            web_utilization=float(options[tier]["web_utilization"])
            if options[tier].get("web_utilization") is not None
            else None,
            tie_beam_profile=str(options[tier].get("tie_beam_profile") or "IPE200"),
            tie_beam_utilization=float(options[tier]["tie_beam_utilization"])
            if options[tier].get("tie_beam_utilization") is not None
            else None,
            bracing_profile=str(options[tier].get("bracing_profile") or "L50x50"),
            bracing_utilization=float(options[tier]["bracing_utilization"])
            if options[tier].get("bracing_utilization") is not None
            else None,
        )
        for tier in order
    ]


def propose_shed_configuration(request: ShedProposalRequest) -> ShedProposalResponse:
    """Build a complete grid_definition draft + engineering rationale."""
    width = float(request.width_mm)
    length = float(request.length_mm)
    height = float(request.height_mm)
    roof_style = request.roof_style
    pitch = 0.0 if roof_style == "flat" else float(request.roof_pitch_deg)

    site = _resolve_site(request)

    rec = compute_structural_recommendations(
        width_mm=width,
        length_mm=length,
        height_mm=height,
        roof_pitch_deg=pitch,
        site=site,
        bay_spacing_override_mm=request.bay_spacing_mm,
        roof_style=roof_style,
    )

    z_spans = _z_spans_for_length(length, rec.bay_spacing_mm)
    n_frames = len(z_spans) + 1

    gd = GridDefinition(
        x_spans=[round(width, 3)],
        z_spans=z_spans,
        height_mm=height,
        roof_pitch_deg=pitch,
        roof_style=roof_style,
        mono_high_side="B",
        use_truss=rec.use_truss,
        truss_type=rec.truss_type if rec.use_truss else "none",
        x_bracing=rec.x_bracing,
        gable_bracing=rec.gable_bracing,
        roof_bracing=rec.roof_bracing,
        sag_rods=rec.sag_rods,
        haunches=rec.haunches,
        fly_braces=rec.fly_braces,
        base_plates=False,
        bottom_chord_restraint=False,
        generate_purlins=True,
        generate_wall_girts=True,
        generate_tie_beams=True,
        purlin_spacing_mm=1200.0,
        girt_spacing_mm=1500.0,
        column_profile=rec.column_profile,
        bracing_profile="L50x50",  # replaced after tier + AI review
        purlin_profile=None,
        girt_profile=None,
        sag_rod_profile=None,
        base_plate_profile=None,
        truss_chord_profile=rec.truss_chord_profile,
        truss_web_profile=rec.truss_web_profile,
        tie_beam_profile="IPE200",
    )

    bay_mm = z_spans[0] if z_spans else rec.bay_spacing_mm
    effective_load = _effective_load(site)
    prelim = estimate_preliminary_loads(
        width_mm=width,
        length_mm=length,
        height_mm=height,
        roof_pitch_deg=pitch,
        bay_spacing_mm=rec.bay_spacing_mm,
        effective_load_index=effective_load,
        site=site,
        roof_style=roof_style,
    )
    is_open = site.exposure == "open" or site.terrain_class in ("0", "II")
    warnings = build_proposal_warnings(
        height_mm=height,
        length_mm=length,
        width_mm=width,
        is_open=is_open,
        loads=prelim,
        use_case=request.use_case,
        roof_style=roof_style,
    )

    tier_options = compute_section_tier_options(
        width_mm=width,
        length_mm=length,
        height_mm=height,
        roof_pitch_deg=pitch,
        site=site,
        bay_spacing_mm=rec.bay_spacing_mm,
        use_truss=rec.use_truss,
        load=effective_load,
        roof_style=roof_style,
    )
    section_tiers = _tier_packages_from_options(tier_options)
    for w in chord_utilization_warnings(section_tiers, use_truss=rec.use_truss):
        if w not in warnings:
            warnings.append(w)
    for w in column_utilization_warnings(
        section_tiers,
        height_mm=height,
        roof_style=roof_style,
    ):
        if w not in warnings:
            warnings.append(w)
    for w in tie_utilization_warnings(section_tiers):
        if w not in warnings:
            warnings.append(w)
    for w in minimum_rules_summary_warning(section_tiers, use_truss=rec.use_truss):
        if w not in warnings:
            warnings.append(w)
    for w in column_alternatives_note(height):
        if w not in warnings:
            warnings.append(w)

    summary = (
        f"{roof_style.replace('_', ' ').title()} · "
        f"{width / 1000:.0f}×{length / 1000:.0f}×{height / 1000:.1f} m · "
        f"{n_frames} frames · "
        f"{'Truss' if rec.use_truss else 'Portal'}"
    )

    ai_review = review_proposal_with_ai(
        summary=summary,
        site=site,
        width_m=width / 1000.0,
        length_m=length / 1000.0,
        height_m=height / 1000.0,
        use_truss=rec.use_truss,
        loads=prelim,
        tiers=section_tiers,
        warnings=warnings,
    )

    active_tier: TierLiteral = "recommended"
    active_pkg = next(t for t in section_tiers if t.tier == active_tier)
    panel_mm = max(0.85 * rec.bay_spacing_mm, 1200.0)
    validation_errors = validate_section_package(
        active_pkg.model_dump(),
        height_mm=height,
        column_axial_kn=prelim.column_axial_kn,
        column_moment_knm=prelim.column_moment_knm,
        chord_axial_kn=prelim.chord_axial_kn if rec.use_truss else None,
        web_axial_kn=prelim.web_axial_kn if rec.use_truss else None,
        web_length_mm=prelim.web_length_mm if rec.use_truss else None,
        tie_beam_axial_kn=prelim.tie_beam_axial_kn,
        tie_beam_length_mm=prelim.tie_beam_length_mm,
        bracing_axial_kn=prelim.bracing_axial_kn,
        bracing_length_mm=prelim.bracing_length_mm,
        panel_length_mm=panel_mm,
        use_truss=rec.use_truss,
    )
    if validation_errors:
        active_pkg = next(t for t in section_tiers if t.tier == "recommended")
        active_tier = "recommended"
        ai_review = AiProposalReview(
            narrative=ai_review.narrative,
            recommended_tier="recommended",
            comparison_summary=ai_review.comparison_summary,
            concerns=ai_review.concerns + validation_errors,
            ai_available=ai_review.ai_available,
        )

    gd = _apply_tier_to_grid(gd, rec, active_pkg)
    rec = rec.model_copy(
        update={
            "column_profile": active_pkg.column_profile,
            "truss_chord_profile": active_pkg.truss_chord_profile,
            "truss_web_profile": active_pkg.truss_web_profile,
        }
    )

    terrain_label = _terrain_label(site.terrain_class)
    rationale = build_proposal_rationale(
        site_location=site.location_label,
        mean_wind_ms=site.mean_wind_ms,
        exposure_proxy_ms=site.design_wind_proxy_ms,
        terrain_label=terrain_label,
        load_index=site.load_index,
        effective_load_index=effective_load,
        rec=rec,
        bay_mm=bay_mm,
        n_frames=n_frames,
        width_m=width / 1000.0,
        length_m=length / 1000.0,
        height_m=height / 1000.0,
        use_case=request.use_case,
        prelim_roof_kn_m2=prelim.roof_pressure_kn_m2,
        prelim_column_m_knm=prelim.column_moment_knm,
        prelim_chord_n_kn=prelim.chord_axial_kn if rec.use_truss else None,
        bracing_profile=gd.bracing_profile or "L50x50",
    )
    if (
        site.surroundings_applied != "auto"
        and site.detected_terrain_class
        and site.detected_load_index is not None
        and (
            site.detected_terrain_class != site.terrain_class
            or abs(site.detected_load_index - site.load_index) > 0.05
        )
    ):
        rationale.append(
            f"Initial map detection: {_terrain_label(site.detected_terrain_class)} · "
            f"load index {site.detected_load_index:.1f} · "
            f"{site.surroundings_applied.replace('_', ' ')} override applied."
        )
    if ai_review.narrative:
        rationale.insert(
            0,
            f"Packages: {ai_review.comparison_summary or ''} {ai_review.narrative}",
        )

    return ShedProposalResponse(
        grid_definition=gd,
        rationale=rationale,
        summary=summary,
        site_context=site,
        recommendations=rec,
        section_tiers=section_tiers,
        warnings=warnings,
        ai_review=ai_review,
        active_tier=active_tier,
    )

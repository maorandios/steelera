"""Deterministic engineering proposal from wizard inputs (Python owns the numbers)."""

from __future__ import annotations

import math

from catalog_loader import has_profile
from schemas.proposal import ShedProposalRequest, ShedProposalResponse
from schemas.spatial_grid import GridDefinition

_TRUSS_WIDTH_THRESHOLD_MM = 15_000.0
_DEFAULT_BAY_MM = 6_000.0
_WIDE_BAY_MM = 6_000.0


def _column_profile_for_height(height_mm: float) -> str:
    if height_mm >= 7_000:
        return "HEA260"
    if height_mm >= 5_500:
        return "HEA240"
    if height_mm >= 4_500:
        return "HEA220"
    return "HEA200"


def _truss_chord_profile(width_mm: float) -> str:
    if width_mm >= 18_000 and has_profile("SHS150x150x6"):
        return "SHS150x150x6"
    if width_mm >= 12_000 and has_profile("SHS120x120x6"):
        return "SHS120x120x6"
    return "IPE200"


def _truss_web_profile(width_mm: float) -> str:
    if width_mm >= 12_000 and has_profile("L60x60x6"):
        return "L60x60x6"
    return "L50x50"


def _z_spans_for_length(length_mm: float, bay_spacing_mm: float | None) -> list[float]:
    spacing = float(bay_spacing_mm or _DEFAULT_BAY_MM)
    if spacing <= 0:
        spacing = _DEFAULT_BAY_MM
    n_bays = max(1, round(length_mm / spacing))
    actual_spacing = length_mm / n_bays
    return [round(actual_spacing, 3) for _ in range(n_bays)]


def _bracing_flags(exposure: str, z_spans: list[float]) -> tuple[bool, bool, bool]:
    """Wall X, roof X, gable X — on by default; extra emphasis when exposed or wide bays."""
    wall = True
    roof = True
    gable = False
    if exposure == "open":
        gable = True
    if any(span >= _WIDE_BAY_MM for span in z_spans):
        roof = True
        wall = True
    return wall, roof, gable


def propose_shed_configuration(request: ShedProposalRequest) -> ShedProposalResponse:
    """Build a complete grid_definition draft + engineering rationale."""
    width = float(request.width_mm)
    length = float(request.length_mm)
    height = float(request.height_mm)
    roof_style = request.roof_style
    pitch = 0.0 if roof_style == "flat" else float(request.roof_pitch_deg)

    z_spans = _z_spans_for_length(length, request.bay_spacing_mm)
    n_frames = len(z_spans) + 1
    use_truss = width >= _TRUSS_WIDTH_THRESHOLD_MM
    truss_type = "pratt" if use_truss else "none"

    column_profile = _column_profile_for_height(height)
    x_bracing, roof_bracing, gable_bracing = _bracing_flags(
        request.exposure, z_spans
    )

    chord = _truss_chord_profile(width) if use_truss else None
    web = _truss_web_profile(width) if use_truss else None

    gd = GridDefinition(
        x_spans=[round(width, 3)],
        z_spans=z_spans,
        height_mm=height,
        roof_pitch_deg=pitch,
        roof_style=roof_style,
        mono_high_side="B",
        use_truss=use_truss,
        truss_type=truss_type,
        x_bracing=x_bracing,
        gable_bracing=gable_bracing,
        roof_bracing=roof_bracing,
        sag_rods=False,
        haunches=False if use_truss else False,
        fly_braces=False,
        base_plates=False,
        bottom_chord_restraint=False,
        generate_purlins=True,
        generate_wall_girts=True,
        generate_tie_beams=True,
        purlin_spacing_mm=1200.0,
        girt_spacing_mm=1500.0,
        column_profile=column_profile,
        bracing_profile="L50x50",
        purlin_profile=None,
        girt_profile=None,
        sag_rod_profile=None,
        base_plate_profile=None,
        truss_chord_profile=chord,
        truss_web_profile=web,
    )

    bay_mm = z_spans[0] if z_spans else _DEFAULT_BAY_MM
    rationale: list[str] = []
    if request.use_case.strip():
        rationale.append(
            f"Use case: {request.use_case.strip()} — optimized for clear internal span "
            f"and standard portal framing."
        )
    rationale.append(
        f"Clear span {width / 1000:.1f} m × {length / 1000:.1f} m length, "
        f"{n_frames} frames at ~{bay_mm / 1000:.1f} m centres."
    )
    if use_truss:
        rationale.append(
            f"Width exceeds {_TRUSS_WIDTH_THRESHOLD_MM / 1000:.0f} m — "
            f"{truss_type.upper()} truss roof with {chord} chords and {web} web diagonals."
        )
    else:
        rationale.append(
            "Moderate width — portal rafter frames (truss not required for this span)."
        )
    rationale.append(
        f"Eave {height / 1000:.1f} m → {column_profile} columns."
    )
    if request.exposure == "open":
        rationale.append(
            "Open/exposed site — full roof and long-wall X-bracing enabled for diaphragm stability."
        )
    else:
        rationale.append(
            "Sheltered site — roof and wall X-bracing still enabled (standard warehouse practice)."
        )
    if any(s >= _WIDE_BAY_MM for s in z_spans):
        rationale.append(
            f"Bays ≥ {_WIDE_BAY_MM / 1000:.0f} m — Python will place diaphragm bracing "
            "in first, middle, and last bays with truss-anchored roof panels."
        )

    summary = (
        f"{roof_style.replace('_', ' ').title()} · "
        f"{width / 1000:.0f}×{length / 1000:.0f}×{height / 1000:.1f} m · "
        f"{n_frames} frames · "
        f"{'Truss' if use_truss else 'Portal'}"
    )

    return ShedProposalResponse(
        grid_definition=gd,
        rationale=rationale,
        summary=summary,
    )

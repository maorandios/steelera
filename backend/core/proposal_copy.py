"""User-facing copy for preliminary structural proposals (not code-compliant design)."""

from __future__ import annotations

from schemas.site import StructuralRecommendations

PROPOSAL_DISCLAIMER = (
    "This is a preliminary model-generation proposal only. "
    "It is not a code-compliant structural design. "
    "Final member sizes, wind loads, connections and foundations must be "
    "verified by a licensed structural engineer."
)

_SECTION_SIZING_NOTE = (
    "Starting sections suggested using preliminary EC3-style capacity checks "
    "and heuristic load assumptions — not a full structural verification."
)


def format_bracing_enabled(rec: StructuralRecommendations) -> str:
    parts: list[str] = []
    if rec.x_bracing:
        parts.append("wall X-bracing")
    if rec.roof_bracing:
        parts.append("roof X-bracing")
    if rec.gable_bracing:
        parts.append("gable X-bracing")
    if rec.sag_rods:
        parts.append("anti-sag rods")
    if not parts:
        return "Bracing: none suggested."
    return f"Bracing enabled: {', '.join(parts)}."


def build_proposal_rationale(
    *,
    site_location: str,
    mean_wind_ms: float,
    exposure_proxy_ms: float,
    terrain_label: str,
    load_index: float,
    effective_load_index: float,
    rec: StructuralRecommendations,
    bay_mm: float,
    n_frames: int,
    width_m: float,
    length_m: float,
    height_m: float,
    use_case: str,
    prelim_roof_kn_m2: float,
    prelim_column_m_knm: float,
    prelim_chord_n_kn: float | None,
    bracing_profile: str = "L50x50",
) -> list[str]:
    """Structured rationale bullets with honest preliminary-design wording."""
    rationale: list[str] = []

    if site_location:
        rationale.append(f"Site: {site_location}.")
    rationale.append(
        f"Climate estimate: mean wind ~{mean_wind_ms:.1f} m/s, "
        f"exposure proxy {exposure_proxy_ms:.1f} m/s. "
        "Code wind speed was not calculated."
    )
    rationale.append(f"Selected terrain: {terrain_label}.")
    rationale.append(f"Internal Steelera load index: {load_index:.1f}.")
    if effective_load_index > load_index + 0.05:
        rationale.append(
            f"Conservative sizing floor applied: effective index "
            f"{effective_load_index:.1f} (internal minimum)."
        )

    bays = bay_mm / 1000.0
    frame_type = (
        f"{rec.truss_type.upper()} truss" if rec.use_truss else "portal frames"
    )
    rationale.append(
        f"Suggested configuration: {frame_type}, {rec.column_profile} columns, "
        f"~{bays:.2f} m bays, {n_frames} frames."
    )

    section_lines = [f"Columns: {rec.column_profile}"]
    if rec.use_truss and rec.truss_chord_profile:
        section_lines.append(f"Truss chords: {rec.truss_chord_profile}")
    if rec.use_truss and rec.truss_web_profile:
        section_lines.append(f"Truss webs: {rec.truss_web_profile}")
    section_lines.append(f"Bracing: {bracing_profile}")
    rationale.append(
        "Suggested starting sections:\n" + "\n".join(f"  - {s}" for s in section_lines)
    )

    rationale.append(format_bracing_enabled(rec))

    load_detail = (
        f"Estimated frame loads for sizing checks: roof {prelim_roof_kn_m2:.2f} kN/m², "
        f"column M ~{prelim_column_m_knm:.0f} kN·m"
    )
    if prelim_chord_n_kn is not None:
        load_detail += f", chord N ~{prelim_chord_n_kn:.0f} kN."
    else:
        load_detail += "."
    rationale.append(f"{_SECTION_SIZING_NOTE} {load_detail}")

    if use_case.strip():
        rationale.append(f"Use case: {use_case.strip()}.")
    rationale.append(
        f"Clear span {width_m:.1f} m × {length_m:.1f} m length, "
        f"{height_m:.1f} m eave."
    )
    rationale.append(PROPOSAL_DISCLAIMER)
    return rationale

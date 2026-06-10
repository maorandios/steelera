"""Re-validate section picks from Python tiers or AI recommendations."""

from __future__ import annotations

from catalog_loader import has_profile
from core.section_props import section_properties
from core.section_selector import (
    MAX_UTILIZATION,
    _bracing_utilization,
    _chord_utilization,
    _column_utilization,
    _member_axial_utilization,
    _tie_beam_utilization,
)

_HARD_UTILIZATION = 0.98


def validate_section_package(
    package: dict[str, str | float | None],
    *,
    height_mm: float,
    column_axial_kn: float,
    column_moment_knm: float,
    chord_axial_kn: float | None,
    web_axial_kn: float | None,
    web_length_mm: float | None,
    tie_beam_axial_kn: float | None,
    tie_beam_length_mm: float | None,
    bracing_axial_kn: float | None = None,
    bracing_length_mm: float | None = None,
    panel_length_mm: float,
    use_truss: bool,
) -> list[str]:
    """Return validation errors (empty = OK)."""
    errors: list[str] = []

    col = str(package.get("column_profile") or "")
    if not has_profile(col):
        errors.append(f"Unknown column profile: {col}")
    else:
        util, _ = _column_utilization(
            section_properties(col),
            axial_kn=column_axial_kn,
            moment_knm=column_moment_knm,
            height_mm=height_mm,
        )
        if util > _HARD_UTILIZATION:
            errors.append(
                f"Column {col} exceeds screening utilization ({util:.2f} > "
                f"{_HARD_UTILIZATION:.2f})."
            )

    if use_truss:
        chord = str(package.get("truss_chord_profile") or "")
        if not has_profile(chord):
            errors.append(f"Unknown truss chord profile: {chord}")
        elif chord_axial_kn is not None:
            util, _ = _chord_utilization(
                section_properties(chord),
                axial_kn=chord_axial_kn,
                panel_length_mm=panel_length_mm,
                prefer_hollow=True,
            )
            if util > _HARD_UTILIZATION:
                errors.append(
                    f"Truss chord {chord} exceeds screening utilization "
                    f"({util:.2f} > {_HARD_UTILIZATION:.2f})."
                )

        web = str(package.get("truss_web_profile") or "")
        if web and not has_profile(web):
            errors.append(f"Unknown truss web profile: {web}")
        elif web and web_axial_kn is not None and web_length_mm is not None:
            util, _ = _member_axial_utilization(
                section_properties(web),
                axial_kn=web_axial_kn,
                length_mm=web_length_mm,
            )
            if util > _HARD_UTILIZATION:
                errors.append(
                    f"Truss web {web} exceeds screening utilization "
                    f"({util:.2f} > {_HARD_UTILIZATION:.2f})."
                )

    tie = str(package.get("tie_beam_profile") or "")
    if tie and not has_profile(tie):
        errors.append(f"Unknown tie beam profile: {tie}")
    elif tie and tie_beam_axial_kn is not None:
        util, _ = _tie_beam_utilization(
            section_properties(tie),
            axial_kn=tie_beam_axial_kn,
        )
        if util > _HARD_UTILIZATION:
            errors.append(
                f"Tie beam {tie} exceeds screening utilization "
                f"({util:.2f} > {_HARD_UTILIZATION:.2f})."
            )

    brace = str(package.get("bracing_profile") or "")
    if brace and not has_profile(brace):
        errors.append(f"Unknown bracing profile: {brace}")
    elif brace and bracing_axial_kn is not None:
        util, _ = _bracing_utilization(
            section_properties(brace),
            axial_kn=bracing_axial_kn,
        )
        if util > _HARD_UTILIZATION:
            errors.append(
                f"Bracing {brace} exceeds screening utilization "
                f"({util:.2f} > {_HARD_UTILIZATION:.2f})."
            )

    return errors


def package_passes_screening(
    package: dict[str, str | float | None],
    **kwargs,
) -> bool:
    return len(validate_section_package(package, **kwargs)) == 0

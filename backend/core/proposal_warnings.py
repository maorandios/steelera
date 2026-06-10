"""Deterministic warnings for preliminary structural proposals."""

from __future__ import annotations

from core.preliminary_loads import PreliminaryLoads
from schemas.proposal import SectionTierPackage

# Chord util below this is dominated by span floors, not force-based sizing.
CHORD_UTIL_MEANINGFUL_MIN = 0.15
# Column util below this — minimum height/span rules dominate, not force demand.
COLUMN_UTIL_MEANINGFUL_MIN = 0.45
# Tie util below this — longitudinal tie force estimate is not governing.
TIE_UTIL_MEANINGFUL_MIN = 0.15

MINIMUM_RULES_SUMMARY = (
    "Some members are sized by minimum geometry/stability rules, not force "
    "demand — utilization shown as — where not meaningful."
)

_FARM_USE_KEYWORDS = (
    "farm",
    "agricultural",
    "agriculture",
    "barn",
    "livestock",
    "poultry",
    "chicken",
    "dairy",
    "grain store",
    "grain storage",
)


def _is_farm_use_case(use_case: str) -> bool:
    text = use_case.strip().lower()
    if not text:
        return False
    if text in ("farm building", "farm shed", "agricultural building"):
        return True
    return any(k in text for k in _FARM_USE_KEYWORDS)


def build_proposal_warnings(
    *,
    height_mm: float,
    length_mm: float,
    width_mm: float,
    is_open: bool,
    loads: PreliminaryLoads,
    use_case: str = "",
    roof_style: str = "duo_pitch",
) -> list[str]:
    warnings: list[str] = []
    height_m = height_mm / 1000.0

    if roof_style == "mono_pitch":
        warnings.append(
            "Mono-pitch roof detected — asymmetric wind uplift and frame drift "
            "should be reviewed; column and bracing demands may differ from "
            "duo-pitch screening."
        )

    if height_mm >= 12_000:
        warnings.append(
            f"Large-height structure detected: {height_m:.1f} m eave. "
            "Second-order effects, column slenderness, and longitudinal "
            "stability must be checked."
        )
    elif height_mm >= 10_000:
        warnings.append(
            f"Tall eave ({height_m:.1f} m) — consider the conservative column "
            "and bracing tier."
        )

    if _is_farm_use_case(use_case) and height_mm >= 12_000:
        warnings.append(
            f"{height_m:.1f} m eave height is unusually high for a farm building. "
            "Confirm this is intentional (e.g. not 9 m entered as 19 m)."
        )

    if length_mm >= 45_000 and is_open:
        warnings.append(
            "Long open building — wall and roof bracing layout should be checked "
            "for diaphragm action."
        )

    if width_mm >= 22_000:
        warnings.append(
            "Wide clear span — truss chord and connection detailing need careful review."
        )

    min_chord = 50.0 + width_mm / 1000.0 * 2.5 + height_mm / 1000.0 * 1.5
    if loads.chord_axial_kn < min_chord and width_mm >= 20_000:
        warnings.append(
            "Estimated chord axial force is a simplified screening value — "
            "verify truss chord forces before final design."
        )

    return warnings


def column_alternatives_note(height_mm: float) -> list[str]:
    """Informational note when rolled sections may not be the practical choice."""
    if height_mm >= 18_000:
        return [
            "Heavy rolled columns shown — built-up, tapered, or box columns are "
            "common at this eave height; adjust column profile if needed."
        ]
    return []


def column_utilization_warnings(
    tiers: list[SectionTierPackage],
    *,
    height_mm: float,
    roof_style: str = "duo_pitch",
) -> list[str]:
    """Warn when column utilization is not meaningful (minimum-rule dominated)."""
    utils = [
        t.column_utilization
        for t in tiers
        if t.column_utilization is not None and t.column_profile
    ]
    if not utils:
        return []

    height_m = height_mm / 1000.0
    if all(u < COLUMN_UTIL_MEANINGFUL_MIN for u in utils):
        style_note = (
            f" and {roof_style.replace('_', '-')} stability rules"
            if roof_style == "mono_pitch"
            else ""
        )
        return [
            "All column packages show low utilization — preliminary column sizing "
            f"is controlled by minimum height/span rules{style_note}, not force "
            "demand. Do not treat column util as code screening."
        ]

    if any(u < COLUMN_UTIL_MEANINGFUL_MIN for u in utils):
        return [
            "Some column utilizations are low — minimum height/span floors may "
            "dominate over the simplified force estimate."
        ]

    return []


def chord_utilization_warnings(
    tiers: list[SectionTierPackage],
    *,
    use_truss: bool,
) -> list[str]:
    """Warn when displayed chord utilization is not meaningful (span-floor dominated)."""
    if not use_truss:
        return []

    utils = [
        t.chord_utilization
        for t in tiers
        if t.chord_utilization is not None and t.truss_chord_profile
    ]
    if not utils:
        return []

    if all(u < CHORD_UTIL_MEANINGFUL_MIN for u in utils):
        return [
            "Chord utilization appears unusually low — chords are set by span minimum "
            "floors, not force-based sizing. Truss chord force model is simplified; "
            "do not treat chord util as code screening."
        ]

    if any(u < CHORD_UTIL_MEANINGFUL_MIN for u in utils):
        return [
            "Some chord utilizations are very low — span minimum floors may dominate "
            "over the simplified truss force estimate."
        ]

    return []


def tie_utilization_warnings(
    tiers: list[SectionTierPackage],
) -> list[str]:
    """Warn when tie-beam utilization is not meaningful."""
    utils = [
        t.tie_beam_utilization
        for t in tiers
        if t.tie_beam_utilization is not None and t.tie_beam_profile
    ]
    if not utils:
        return []

    if all(u < TIE_UTIL_MEANINGFUL_MIN for u in utils):
        return [
            "Tie-beam utilization appears very low — ties are set by span/practice "
            "minimums, not the simplified wind thrust estimate."
        ]

    if any(u < TIE_UTIL_MEANINGFUL_MIN for u in utils):
        return [
            "Some tie-beam utilizations are very low — minimum size rules may "
            "dominate over the simplified force estimate."
        ]

    return []


def minimum_rules_summary_warning(
    tiers: list[SectionTierPackage],
    *,
    use_truss: bool,
) -> list[str]:
    """Single umbrella note when multiple member utils are floor-dominated."""
    col_low = any(
        t.column_utilization is not None
        and t.column_utilization < COLUMN_UTIL_MEANINGFUL_MIN
        for t in tiers
    )
    chord_low = use_truss and any(
        t.chord_utilization is not None
        and t.chord_utilization < CHORD_UTIL_MEANINGFUL_MIN
        for t in tiers
    )
    tie_low = any(
        t.tie_beam_utilization is not None
        and t.tie_beam_utilization < TIE_UTIL_MEANINGFUL_MIN
        for t in tiers
    )
    kinds = sum([col_low, chord_low, tie_low])
    if kinds >= 2 or (col_low and tie_low):
        return [MINIMUM_RULES_SUMMARY]
    return []

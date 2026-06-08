"""Extract catalog profile choices from user text and merge into grid layouts."""

from __future__ import annotations

import re
from typing import Any

from catalog_loader import has_profile
from core.grid_layout_utils import ensure_layout_members
from schemas.spatial_grid import GridDefinition, StructuralGridLayout

_PROFILE_FIELDS = (
    "column_profile",
    "bracing_profile",
    "purlin_profile",
    "girt_profile",
    "sag_rod_profile",
    "base_plate_profile",
    "truss_chord_profile",
    "truss_web_profile",
)

_TRUSS_PROFILE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "truss_chord_profile",
        re.compile(
            r"(?:truss\s+chords?(?:\s*\([^)]*\))?|(?:top|bottom)\s+chords?|"
            r"tc\s*(?:&|and)\s*bc)\s*[-:=]\s*"
            r"([A-Za-z][A-Za-z0-9xX.\-/]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "truss_web_profile",
        re.compile(
            r"(?:truss\s+web(?:\s+diagonals?)?|web\s+diagonals?)\s*[-:=]\s*"
            r"([A-Za-z][A-Za-z0-9xX.\-/]+)",
            re.IGNORECASE,
        ),
    ),
)

# girt_profile: C220x2.0  |  girt profile C220x2.0  |  girt C220x2.0
_VALUE = r"([A-Za-z][A-Za-z0-9xX.\-/]+)"


def _field_pattern(field: str) -> re.Pattern[str]:
    alias = field.replace("_", "[_\\s]")
    role = field.split("_")[0]
    return re.compile(
        rf"(?:{alias}|{role}\s+profile)\s*[:=]?\s*{_VALUE}",
        re.IGNORECASE,
    )


_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    field: _field_pattern(field) for field in _PROFILE_FIELDS
}


def extract_profiles_from_text(text: str) -> dict[str, str]:
    """Parse explicit profile lines from a chat / checklist prompt."""
    if not text or not text.strip():
        return {}

    found: dict[str, str] = {}
    for field, pattern in _TRUSS_PROFILE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().rstrip(",.;")
        if value and has_profile(value):
            found[field] = value
    for field, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().rstrip(",.;")
        if value and has_profile(value):
            found[field] = value
    return found


def _profiles_from_members(
    members: list[Any],
) -> dict[str, str]:
    """Infer catalog profiles from an existing structural member BOM."""
    by_type: dict[str, str] = {}
    for member in members:
        et = getattr(member, "element_type", None) or member.get("element_type")
        profile = getattr(member, "profile", None) or member.get("profile")
        if not et or not profile:
            continue
        if et == "column" and "column_profile" not in by_type:
            by_type["column_profile"] = str(profile)
        elif et == "wall_girt" and "girt_profile" not in by_type:
            by_type["girt_profile"] = str(profile)
        elif et == "purlin" and "purlin_profile" not in by_type:
            by_type["purlin_profile"] = str(profile)
        elif et == "bracing" and "bracing_profile" not in by_type:
            by_type["bracing_profile"] = str(profile)
        elif et == "sag_rod" and "sag_rod_profile" not in by_type:
            by_type["sag_rod_profile"] = str(profile)
        elif et == "truss_chord" and "truss_chord_profile" not in by_type:
            by_type["truss_chord_profile"] = str(profile)
        elif et == "truss_web" and "truss_web_profile" not in by_type:
            by_type["truss_web_profile"] = str(profile)
    return by_type


def merge_profiles_into_grid_definition(
    grid_def: GridDefinition,
    overrides: dict[str, str],
    *,
    force_fields: frozenset[str] | None = None,
) -> GridDefinition:
    """Apply profile overrides; ``force_fields`` replaces even when grid already has a value."""
    if not overrides:
        return grid_def

    force = force_fields or frozenset()
    updates: dict[str, str] = {}
    for field in _PROFILE_FIELDS:
        existing = getattr(grid_def, field, None)
        value = overrides.get(field)
        if not value or not has_profile(value):
            continue
        if existing and field not in force:
            continue
        updates[field] = value
    if not updates:
        return grid_def
    return grid_def.model_copy(update=updates)


def apply_profile_overrides_to_layout(
    layout: StructuralGridLayout,
    *,
    user_text: str = "",
) -> StructuralGridLayout:
    """
    Fill grid_definition profiles from the user prompt and/or member BOM,
    then rebuild structural_members so catalog sections match.
    """
    text_overrides = extract_profiles_from_text(user_text)
    member_overrides = _profiles_from_members(layout.structural_members)
    overrides = {**member_overrides, **text_overrides}

    gd = merge_profiles_into_grid_definition(
        layout.grid_definition,
        overrides,
        force_fields=frozenset(text_overrides.keys()),
    )
    if gd is layout.grid_definition:
        return layout

    refreshed = layout.model_copy(
        update={"grid_definition": gd, "structural_members": []},
    )
    return ensure_layout_members(refreshed)

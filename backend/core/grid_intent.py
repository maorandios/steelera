"""Parse structural intent from chat prompts and merge into grid definitions."""

from __future__ import annotations

import re

from schemas.spatial_grid import GridDefinition

_TRUSS_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("scissor", re.compile(r"scissor", re.IGNORECASE)),
    ("queen_post", re.compile(r"queen[\s-]?post", re.IGNORECASE)),
    ("king_post", re.compile(r"king[\s-]?post", re.IGNORECASE)),
    ("fink", re.compile(r"\bfink\b", re.IGNORECASE)),
    ("warren", re.compile(r"\bwarren\b", re.IGNORECASE)),
    ("howe", re.compile(r"\bhowe\b", re.IGNORECASE)),
    ("pratt", re.compile(r"\bpratt\b", re.IGNORECASE)),
)

_BOOL_FIELDS = (
    "use_truss",
    "x_bracing",
    "gable_bracing",
    "roof_bracing",
    "sag_rods",
    "haunches",
    "fly_braces",
    "base_plates",
    "bottom_chord_restraint",
    "generate_wall_girts",
    "generate_tie_beams",
)


def extract_grid_intent_from_text(text: str) -> dict[str, bool | str]:
    """Best-effort parse of user-requested grid toggles from natural language."""
    if not text or not text.strip():
        return {}

    t = text.lower()
    intent: dict[str, bool | str] = {}

    if re.search(
        r"\bmono[\s-]?pitch\b|\bmonopitch\b|single[\s-]slope|\bmono[\s-]shed\b",
        t,
    ):
        intent["roof_style"] = "mono_pitch"
    elif re.search(r"\bflat[\s-]?roof\b|\bflat[\s-]?pitch\b", t):
        intent["roof_style"] = "flat"
    elif re.search(r"\bduo[\s-]?pitch\b|\bduopitch\b|\bgable[\s-]?roof\b", t):
        intent["roof_style"] = "duo_pitch"

    if re.search(r"\btruss(?:es)?\b", t) and not re.search(
        r"\bno[\s-]?truss|\bwithout[\s-]?truss", t
    ):
        intent["use_truss"] = True

    for truss_type, pattern in _TRUSS_TYPE_PATTERNS:
        if pattern.search(text):
            intent["use_truss"] = True
            intent["truss_type"] = truss_type
            break

    if re.search(r"bottom[\s-]?chord[\s-]?restraint|bc[\s-]?restraint", t):
        intent["bottom_chord_restraint"] = True
        intent["use_truss"] = True

    if re.search(r"\bsag[\s-]?rod", t):
        intent["sag_rods"] = True

    if re.search(r"\bbase[\s-]?plate", t):
        intent["base_plates"] = True

    if re.search(r"\bgirt", t) and not re.search(r"\bno[\s-]?girt", t):
        intent["generate_wall_girts"] = True

    if re.search(r"\bpurlin", t):
        pass  # always generated; spacing handled separately

    if re.search(r"roof[\s-]?bracing|bracing[\s-]?in[\s-]?the[\s-]?roof", t):
        intent["roof_bracing"] = True

    if re.search(r"gable[\s-]?bracing|end[\s-]?wall[\s-]?bracing", t):
        intent["gable_bracing"] = True

    if re.search(
        r"side[\s-]?bracing|wall[\s-]?bracing|long[\s-]?wall[\s-]?bracing|x[\s-]?bracing",
        t,
    ) or (
        re.search(r"\bbracing\b", t)
        and "roof bracing" not in t
        and "gable bracing" not in t
    ):
        intent["x_bracing"] = True

    pitch_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:°|deg(?:ree)?s?|pitch)",
        text,
        re.IGNORECASE,
    )
    if pitch_match:
        intent["roof_pitch_deg"] = float(pitch_match.group(1))

    return intent


def merge_grid_intent_into_definition(
    grid_def: GridDefinition,
    intent: dict[str, bool | str],
) -> GridDefinition:
    """Apply parsed user intent; explicit prompt wins over AI grid defaults."""
    if not intent:
        return grid_def

    updates: dict[str, bool | str] = {}
    for key, value in intent.items():
        if key in _BOOL_FIELDS and isinstance(value, bool):
            updates[key] = value
        elif key == "roof_style" and value in ("duo_pitch", "mono_pitch", "flat"):
            updates[key] = value
        elif key == "truss_type" and isinstance(value, str):
            updates[key] = value
            updates["use_truss"] = True
        elif key == "roof_pitch_deg" and isinstance(value, (int, float)):
            updates["roof_pitch_deg"] = float(value)

    if not updates:
        return grid_def

    if updates.get("use_truss") and updates.get("truss_type") is None:
        existing = str(getattr(grid_def, "truss_type", "none") or "none")
        if existing == "none":
            updates["truss_type"] = "pratt"

    return grid_def.model_copy(update=updates)

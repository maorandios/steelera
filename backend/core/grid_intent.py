"""Parse structural intent from chat prompts (fallback only — AI tool args win)."""

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

_BOOL_FIELDS = frozenset({
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
    "generate_purlins",
    "generate_tie_beams",
})

# Feature labels users type in engineering specs (order: longer phrases first).
_FEATURE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("generate_purlins", ("roof purlin", "purlin", "purlins")),
    ("generate_wall_girts", ("wall girt", "girts", "girt")),
    ("roof_bracing", (
        "roof cross-bracing",
        "roof cross bracing",
        "roof x-bracing",
        "roof x bracing",
        "roof bracing",
    )),
    ("x_bracing", (
        "wall cross-bracing",
        "wall cross bracing",
        "side wall bracing",
        "long wall bracing",
        "wall x-bracing",
        "wall x bracing",
        "wall bracing",
        "x-bracing",
        "x bracing",
    )),
    ("gable_bracing", ("gable bracing", "end wall bracing", "gable x-bracing")),
    ("sag_rods", ("sag rod", "sag rods", "anti-sag")),
    ("use_truss", ("truss", "trusses")),
    ("bottom_chord_restraint", ("bottom chord restraint", "bc restraint")),
    ("base_plates", ("base plate", "base plates")),
    ("fly_braces", ("fly brace", "fly braces", "flange brace")),
    ("haunches", ("haunch", "haunches")),
    ("generate_tie_beams", ("tie beam", "tie beams", "longitudinal tie")),
)

_DISABLED_RE = re.compile(
    r"\b(?:disabled|disable|off|no|none|zero|0|do\s+not\s+generate|don't\s+generate|without)\b",
    re.IGNORECASE,
)
_ENABLED_RE = re.compile(
    r"\b(?:enabled|enable|on|yes|generate|include|with)\b",
    re.IGNORECASE,
)


def _line_for_match(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end]


def _feature_tristate_from_text(text: str, aliases: tuple[str, ...]) -> bool | None:
    """
    Return True/False when a feature line states ENABLED/DISABLED near an alias.
    None when the prompt does not clearly mention that feature.
    """
    if not text or not text.strip():
        return None

    lower = text.lower()
    for alias in aliases:
        pattern = re.compile(rf"\b{re.escape(alias.lower())}\b", re.IGNORECASE)
        for match in pattern.finditer(lower):
            line = _line_for_match(lower, match.start())
            if _DISABLED_RE.search(line):
                return False
            if _ENABLED_RE.search(line):
                return True
    return None


def extract_grid_intent_from_text(text: str) -> dict[str, bool | str | float]:
    """Best-effort parse of user-requested grid toggles from natural language."""
    if not text or not text.strip():
        return {}

    t = text.lower()
    intent: dict[str, bool | str | float] = {}

    if re.search(
        r"\bmono[\s-]?pitch\b|\bmonopitch\b|single[\s-]slope|\bmono[\s-]shed\b",
        t,
    ):
        intent["roof_style"] = "mono_pitch"
    elif re.search(r"\bflat[\s-]?roof\b|\bflat[\s-]?pitch\b", t):
        intent["roof_style"] = "flat"
    elif re.search(r"\bduo[\s-]?pitch\b|\bduopitch\b|\bgable[\s-]?roof\b", t):
        intent["roof_style"] = "duo_pitch"

    if re.search(r"\btruss(?:es)?\b", t):
        state = _feature_tristate_from_text(text, ("truss", "trusses"))
        if state is not False:
            intent["use_truss"] = True

    for truss_type, pattern in _TRUSS_TYPE_PATTERNS:
        if pattern.search(text):
            intent["use_truss"] = True
            intent["truss_type"] = truss_type
            break

    for field, aliases in _FEATURE_ALIASES:
        state = _feature_tristate_from_text(text, aliases)
        if state is not None:
            intent[field] = state

    # Generic "bracing" when not scoped to roof/gable/wall lines above.
    if "x_bracing" not in intent and "roof_bracing" not in intent:
        if re.search(r"\bbracing\b", t) and not re.search(
            r"roof[\s-]?(?:cross[\s-]?)?bracing|gable[\s-]?bracing|wall[\s-]?(?:cross[\s-]?)?bracing",
            t,
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
    intent: dict[str, bool | str | float],
    *,
    fill_gaps_only: bool = True,
) -> GridDefinition:
    """
    Apply parsed user intent.

    When ``fill_gaps_only`` is True (default), boolean flags from the AI tool
    are never overwritten — only non-boolean hints (pitch, truss type, roof style)
    fill missing values.
    """
    if not intent:
        return grid_def

    updates: dict[str, bool | str | float] = {}
    for key, value in intent.items():
        if key in _BOOL_FIELDS and isinstance(value, bool):
            if fill_gaps_only:
                continue
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

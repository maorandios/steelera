"""
European structural steel catalog (static).

All section dimensions in millimeters (EN 10365 typical values):
  h  — overall section height
  b  — flange width
  tw — web thickness
  tf — flange thickness
"""

from typing import TypedDict


class CatalogProfile(TypedDict):
    family: str
    h: float
    b: float
    tw: float
    tf: float


EUROPEAN_PROFILES: dict[str, CatalogProfile] = {
    "IPE200": {
        "family": "IPE",
        "h": 200.0,
        "b": 100.0,
        "tw": 5.6,
        "tf": 8.5,
    },
    "IPE300": {
        "family": "IPE",
        "h": 300.0,
        "b": 150.0,
        "tw": 7.1,
        "tf": 10.7,
    },
    "HEA200": {
        "family": "HEA",
        "h": 190.0,
        "b": 200.0,
        "tw": 6.5,
        "tf": 10.0,
    },
    "C150": {
        "family": "C",
        "h": 150.0,
        "b": 75.0,
        "tw": 4.0,
        "tf": 12.0,
    },
}

CATALOG_PROFILE_NAMES: tuple[str, ...] = tuple(EUROPEAN_PROFILES.keys())


def get_profile(name: str) -> CatalogProfile:
    """Return catalog dimensions for a standard profile name (case-insensitive)."""
    key = name.strip().upper().replace(" ", "")
    profile = EUROPEAN_PROFILES.get(key)
    if profile is None:
        available = ", ".join(CATALOG_PROFILE_NAMES)
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")
    return profile


def list_profiles() -> list[dict[str, str | float]]:
    """Serialize catalog for prompts or API discovery."""
    return [
        {
            "profile_name": name,
            "family": data["family"],
            "h_mm": data["h"],
            "b_mm": data["b"],
            "tw_mm": data["tw"],
            "tf_mm": data["tf"],
        }
        for name, data in EUROPEAN_PROFILES.items()
    ]

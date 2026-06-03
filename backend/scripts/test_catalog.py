"""Test catalog + geometry. Run from backend/: python scripts/test_catalog.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog_loader import get_profile, list_profiles
from core.geometry_engine import parse_add_structural_element

print("Catalog:", list_profiles())

el = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 6, "unit": "m"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "IPE200",
        "axis": "y",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": "NONE",
        "anchor_point": "NONE",
    },
    0,
)
assert el.profile_name == "IPE200"
assert el.section_mm is not None
assert el.section_mm.h == 200.0
assert el.section_mm.b == 100.0
assert el.section_source == "catalog"
print("IPE200 element:", el.model_dump())
print("Catalog geometry OK")

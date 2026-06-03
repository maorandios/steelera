"""Test column at CENTER vs END of horizontal beam."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geometry_engine import parse_add_structural_element

beam = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 1000, "unit": "mm"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "IPE200",
        "axis": "x",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": "NONE",
        "anchor_point": "NONE",
    },
    0,
    existing_elements=[],
)

col_end = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 1000, "unit": "mm"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "HEA200",
        "axis": "y",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": beam.id,
        "anchor_point": "END",
    },
    1,
    existing_elements=[beam],
)

col_center = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 1000, "unit": "mm"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "HEA200",
        "axis": "y",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": beam.id,
        "anchor_point": "CENTER",
    },
    2,
    existing_elements=[beam],
)

assert col_end.nodes["bottom"][0] == 1000.0
assert col_center.nodes["bottom"][0] == 500.0
assert col_end.nodes["bottom"][0] != col_center.nodes["bottom"][0]
print("END column x:", col_end.nodes["bottom"][0])
print("CENTER column x:", col_center.nodes["bottom"][0])
print("Beam top_center:", beam.nodes["top_center"])
print("CENTER anchoring OK")

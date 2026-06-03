"""Test column on top of horizontal beam at END — must grow upward (+Y)."""

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

column = parse_add_structural_element(
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

beam_top_end_y = beam.nodes["top_end"][1]
col_bottom_y = column.position_mm["y"]
col_top_y = column.nodes["top"][1]

print("Beam top_end:", beam.nodes["top_end"])
print("Column bottom:", column.nodes["bottom"])
print("Column top:", column.nodes["top"])

assert col_bottom_y == beam_top_end_y, "Column base must sit on beam top at end"
assert col_top_y == col_bottom_y + 1000.0, "Column must extend upward 1000mm"
assert col_top_y > col_bottom_y, "Column must grow in +Y, not downward"
print("Column-on-beam END anchoring OK")

"""Test spatial anchoring: beam on TOP of column via connection nodes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geometry_engine import parse_add_structural_element
from core.spatial_context import format_project_context

column = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 4, "unit": "m"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "IPE200",
        "axis": "y",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": "NONE",
        "anchor_point": "NONE",
    },
    0,
    existing_elements=[],
)

assert column.nodes["bottom"] == [0.0, 0.0, 0.0]
assert column.nodes["top"] == [0.0, 4000.0, 0.0]

print(format_project_context([column]))
print()

beam = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 5, "unit": "m"},
        "width": {"value": 0, "unit": "mm"},
        "profile_name": "IPE200",
        "axis": "x",
        "position": {"x": 0, "y": 0, "z": 0},
        "anchor_element_id": column.id,
        "anchor_point": "TOP",
    },
    1,
    existing_elements=[column],
)

print("Column top node:", column.nodes["top"])
print("Beam start node:", beam.nodes["start"])
print("Beam position_mm:", beam.position_mm)

assert beam.nodes["start"] == column.nodes["top"], "Beam start must snap to column top node"
assert beam.position_mm["y"] == 4000.0
assert beam.nodes["end"] == [5000.0, 4000.0, 0.0]
assert beam.anchor_element_id == column.id
print("Spatial node anchoring OK")

"""Test ARRAY macro: duplicate column to the right (+X) with 2000 mm spacing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geometry_engine import apply_macro_action, parse_add_structural_element

column = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 1000, "unit": "mm"},
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

elements, summary = apply_macro_action(
    {
        "target_element_id": column.id,
        "action_type": "ARRAY",
        "count": 5,
        "spacing": {"value": 2000, "unit": "mm"},
        "axis": "X",
    },
    [column],
)

assert summary["success"] is True
assert summary["action"] == "ARRAY"
assert len(elements) == 6

xs = sorted(float(el.position_mm["x"]) for el in elements)
expected = [0.0, 2000.0, 4000.0, 6000.0, 8000.0, 10000.0]
assert xs == expected, f"Expected X positions {expected}, got {xs}"

ys = [float(el.position_mm["y"]) for el in elements]
assert all(y == 0.0 for y in ys), f"Y should stay at 0, got {ys}"

print("PASS: 5 copies along +X at 2000 mm spacing")
for el in elements:
    print(f"  {el.id}: x={el.position_mm['x']}, y={el.position_mm['y']}")

"""Local test for geometry_engine (no OpenAI). Run: python scripts/test_milestone1.py"""

from core.geometry_engine import parse_add_structural_element, to_millimeters

assert to_millimeters(6, "auto") == 6000
assert to_millimeters(200, "auto") == 200
assert to_millimeters(3, "m") == 3000

el = parse_add_structural_element(
    {
        "shape_type": "I-beam",
        "length": {"value": 4.5, "unit": "m"},
        "width": {"value": 200, "unit": "mm"},
        "position": {"x": 0, "y": 0, "z": 0},
    },
    0,
)
print("Sample element (mm):", el.model_dump())
print("Milestone 1 geometry_engine OK")

"""Test modify_shed_assembly logic without OpenAI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geometry_engine import macro_members_to_project_elements
from core.shed_geometry import generate_shed_macro
from core.shed_assembly import apply_modify_shed_assembly
import json

macro = generate_shed_macro(
    "shed_1",
    x_spans=[12000],
    z_spans=[6000, 6000, 6000, 6000],
    height=4000,
)
elements = macro_members_to_project_elements(macro)

updated, summary = apply_modify_shed_assembly(
    elements,
    json.dumps({"height": 5000, "width": None, "length": None, "roof_pitch_deg": None}),
)

assert summary["success"] is True
cols = [e for e in updated if e.id.startswith("shed-col")]
assert cols[0].length_mm == 5000.0

print("PASS: modify_shed_assembly height -> 5000 mm")
print("  applied:", summary["applied_params"])

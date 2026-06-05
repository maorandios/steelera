"""Test AI BOM renderer (no OpenAI). Run: python scripts/test_structural_renderer.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.structural_renderer import apply_structural_layout

payload = {
    "assembly_id": "shed_1",
    "replace_existing": True,
    "elements": [
        {
            "element_type": "column",
            "profile": "HEA200",
            "start_node": [0, 0, 0],
            "end_node": [0, 4000, 0],
            "rotation_deg": 0,
        },
        {
            "element_type": "column",
            "profile": "HEA200",
            "start_node": [10000, 0, 0],
            "end_node": [10000, 4000, 0],
            "rotation_deg": 0,
        },
        {
            "element_type": "rafter",
            "profile": "IPE200",
            "start_node": [0, 4000, 0],
            "end_node": [5000, 4878, 0],
            "rotation_deg": 10.62,
        },
        {
            "element_type": "rafter",
            "profile": "IPE200",
            "start_node": [10000, 4000, 0],
            "end_node": [5000, 4878, 0],
            "rotation_deg": -10.62,
        },
    ],
}

elements, summary = apply_structural_layout(
    json.dumps(payload),
    [],
    replace_session=True,
)
assert summary["success"] is True
assert len(elements) == 4
assert elements[0].nodes["bottom"] == [0.0, 0.0, 0.0]
assert elements[0].nodes["top"] == [0.0, 4000.0, 0.0]
assert elements[0].element_type == "column"
print("PASS: structural_renderer", summary)

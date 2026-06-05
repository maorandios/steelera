"""Quick check: parametric body parses and HTTP endpoint accepts it."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routers.macro import _parse_generate_shed_body

PAYLOAD = {
    "assembly_id": "shed_1",
    "replace_existing": True,
    "global_parameters": {
        "height_mm": 4000,
        "roof_pitch_deg": 10,
        "roof_style": "duo_pitch",
    },
    "grid_layout": {"x_spans": [10000], "z_spans": [5000, 5000]},
    "bays_configuration": [
        {
            "bay_index": 0,
            "use_truss": True,
            "truss_type": "pratt",
            "x_bracing_left_wall": True,
            "x_bracing_right_wall": True,
            "wall_girts": True,
            "sag_rods": True,
        },
        {
            "bay_index": 1,
            "use_truss": True,
            "truss_type": "pratt",
            "x_bracing_left_wall": True,
            "x_bracing_right_wall": True,
            "wall_girts": True,
            "sag_rods": True,
        },
    ],
    "purlin_spacing_mm": 1200,
    "girt_spacing_mm": 1500,
    "generate_tie_beams": True,
}

layout = _parse_generate_shed_body(PAYLOAD)
print("parse OK:", layout.assembly_id, "members", len(layout.structural_members))

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/macro/generate-shed",
    data=json.dumps(PAYLOAD).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        print("HTTP OK total_generated:", data["counts"]["total_generated"])
except urllib.error.HTTPError as exc:
    print("HTTP", exc.code, exc.read().decode()[:800])

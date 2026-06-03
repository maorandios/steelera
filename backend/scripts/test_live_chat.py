"""Live two-step chat test: column then anchored beam via POST /api/chat."""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.env_loader import load_env

load_env()

API = "http://127.0.0.1:8000/api/chat"


def post_chat(messages: list[dict], project_elements: list | None = None) -> dict:
    body = {
        "messages": messages,
        "projectElements": project_elements or [],
        "projectState": {"version": 3, "projectElements": project_elements or []},
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main() -> None:
    print("=== Step 1: Add IPE200 column 4m at origin ===")
    r1 = post_chat(
        [{"role": "user", "content": "Add an IPE200 column 4 meters tall at the origin."}]
    )
    elements = r1.get("projectElements") or []
    print("Assistant:", r1["message"]["content"][:200])
    print("Statuses:", r1.get("statuses"))
    print("Elements:", len(elements))
    if not elements:
        print("FAIL: no elements returned")
        sys.exit(1)
    col = elements[0]
    print("Column:", col["id"], "pos=", col["position_mm"], "size=", col["size_mm"])
    col_top = col["position_mm"]["y"] + col["size_mm"]["y"]
    print("Column top Y:", col_top)

    print("\n=== Step 2: Add beam on top of column ===")
    history = [
        {"role": "user", "content": "Add an IPE200 column 4 meters tall at the origin."},
        {"role": "assistant", "content": r1["message"]["content"]},
        {
            "role": "user",
            "content": "Add an IPE200 beam 5 meters long on top of the column.",
        },
    ]
    r2 = post_chat(history, elements)
    elements2 = r2.get("projectElements") or []
    print("Assistant:", r2["message"]["content"][:200])
    print("Statuses:", r2.get("statuses"))
    print("Elements:", len(elements2))
    if len(elements2) < 2:
        print("FAIL: expected 2 elements, got", len(elements2))
        print(json.dumps(r2, indent=2))
        sys.exit(1)

    beam = elements2[-1]
    print("Beam:", beam["id"], "pos=", beam["position_mm"], "anchor=", beam.get("anchor_element_id"), beam.get("anchor_point"))
    beam_y = beam["position_mm"]["y"]
    if abs(beam_y - col_top) < 1.0:
        print(f"PASS: beam Y ({beam_y}) matches column top ({col_top})")
    else:
        print(f"WARN: beam Y ({beam_y}) != column top ({col_top}) — check anchoring")
    print("\nLive chat test complete.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode())
        sys.exit(1)

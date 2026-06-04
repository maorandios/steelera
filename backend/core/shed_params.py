"""Infer and merge portal-frame shed macro parameters from assembly members."""

from __future__ import annotations

from typing import Any

from schemas.elements import ProjectElementMm

DEFAULT_SHED_PARAMS: dict[str, float | list[float]] = {
    "x_spans": [3000.0, 7000.0, 10000.0, 5000.0],
    "z_spans": [5000.0, 5000.0, 5000.0, 5000.0, 5000.0, 5000.0],
    "width": 25000.0,
    "length": 30000.0,
    "height": 4000.0,
    "roof_pitch_deg": 10.0,
    "purlin_spacing": 1200.0,
}

SHED_ASSEMBLY_ID = "shed_1"


def _infer_spans_from_positions(coords: list[float]) -> list[float]:
    xs = sorted({round(c, 3) for c in coords})
    if len(xs) >= 2:
        return [round(xs[i] - xs[i - 1], 3) for i in range(1, len(xs))]
    if len(xs) == 1 and xs[0] > 0:
        return [xs[0]]
    return []


def infer_shed_params_from_elements(
    members: list[ProjectElementMm],
) -> dict[str, float | list[float]]:
    """Derive shed dimensions from an existing shed_1 assembly in the model."""
    if not members:
        return dict(DEFAULT_SHED_PARAMS)

    cols = [element for element in members if element.id.startswith("shed-col")]
    purlins = [element for element in members if element.id.startswith("shed-purl")]
    left_rafters = [
        element for element in members if element.id.startswith("shed-raf-L")
    ]

    x_spans = _infer_spans_from_positions(
        [float(element.position_mm["x"]) for element in cols]
    )
    z_spans = _infer_spans_from_positions(
        [float(element.position_mm["z"]) for element in cols]
    )
    if not x_spans:
        x_spans = list(DEFAULT_SHED_PARAMS["x_spans"])  # type: ignore[arg-type]
    if not z_spans:
        z_spans = list(DEFAULT_SHED_PARAMS["z_spans"])  # type: ignore[arg-type]

    width = sum(x_spans)
    length = sum(z_spans)
    height = float(cols[0].length_mm) if cols else float(DEFAULT_SHED_PARAMS["height"])

    pitch = float(DEFAULT_SHED_PARAMS["roof_pitch_deg"])
    if left_rafters and left_rafters[0].rotation_euler_deg:
        pitch = float(left_rafters[0].rotation_euler_deg[2])

    return {
        "x_spans": x_spans,
        "z_spans": z_spans,
        "width": width,
        "length": length,
        "height": height,
        "roof_pitch_deg": pitch,
        "purlin_spacing": float(DEFAULT_SHED_PARAMS["purlin_spacing"]),
    }


def merge_shed_param_overrides(
    current: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Apply optional tool/API overrides (mm and degrees)."""
    from core.geometry_engine import (
        cumulative_positions_from_spans,
        parse_bay_spans_mm,
    )

    merged = dict(current)
    for key in ("height", "roof_pitch_deg", "purlin_spacing"):
        value = overrides.get(key)
        if value is None:
            continue
        merged[key] = float(value)

    if overrides.get("x_spans") is not None:
        spans = parse_bay_spans_mm(overrides["x_spans"])
        merged["x_spans"] = spans
        merged["width"] = cumulative_positions_from_spans(spans)[-1]
    elif overrides.get("width") is not None:
        merged["width"] = float(overrides["width"])
        merged["x_spans"] = [merged["width"]]

    if overrides.get("z_spans") is not None:
        spans = parse_bay_spans_mm(overrides["z_spans"])
        merged["z_spans"] = spans
        merged["length"] = cumulative_positions_from_spans(spans)[-1]
    elif overrides.get("length") is not None:
        merged["length"] = float(overrides["length"])
        if overrides.get("frame_spacing"):
            from core.geometry_engine import _frame_positions_along

            positions = _frame_positions_along(
                merged["length"], float(overrides["frame_spacing"])
            )
            merged["z_spans"] = [
                round(positions[i] - positions[i - 1], 3)
                for i in range(1, len(positions))
            ]

    return merged


def shed_members_in(
    elements: list[ProjectElementMm],
    assembly_id: str = SHED_ASSEMBLY_ID,
) -> list[ProjectElementMm]:
    return [
        element
        for element in elements
        if element.assembly_id == assembly_id
    ]

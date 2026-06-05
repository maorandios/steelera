"""Infer and merge portal-frame shed macro parameters from assembly members."""

from __future__ import annotations

from typing import Any

from schemas.elements import ProjectElementMm

DEFAULT_SHED_PARAMS: dict[str, float | list[float] | str | bool | None] = {
    "x_spans": [3000.0, 7000.0, 10000.0, 5000.0],
    "z_spans": [5000.0, 5000.0, 5000.0, 5000.0, 5000.0, 5000.0],
    "width": 25000.0,
    "length": 30000.0,
    "height": 4000.0,
    "roof_pitch_deg": 10.0,
    "roof_style": "duo_pitch",
    "purlin_spacing": 1200.0,
    "girt_spacing_mm": 1500.0,
    "purlin_profile": None,
    "girt_profile": None,
    "sag_rod_profile": None,
    "base_plate_profile": None,
    "use_truss": False,
    "use_bracing": False,
    "use_sag_rods": False,
    "generate_wall_girts": True,
    "generate_tie_beams": True,
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

    out: dict[str, Any] = dict(DEFAULT_SHED_PARAMS)
    out.update(
        {
            "x_spans": x_spans,
            "z_spans": z_spans,
            "width": width,
            "length": length,
            "height": height,
            "roof_pitch_deg": pitch,
        }
    )
    return out


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
    for key in ("height", "roof_pitch_deg", "purlin_spacing", "girt_spacing_mm"):
        value = overrides.get(key)
        if value is None:
            continue
        merged[key] = float(value)

    if overrides.get("roof_style") is not None:
        key = str(overrides["roof_style"]).strip().lower().replace("-", "_")
        if key in ("duo_pitch", "mono_pitch", "flat"):
            merged["roof_style"] = key

    for key in (
        "purlin_profile",
        "girt_profile",
        "sag_rod_profile",
        "base_plate_profile",
    ):
        if overrides.get(key) is not None:
            value = str(overrides[key]).strip()
            merged[key] = value or None

    for key in (
        "use_truss",
        "use_bracing",
        "use_sag_rods",
        "generate_wall_girts",
        "generate_tie_beams",
    ):
        if overrides.get(key) is not None:
            merged[key] = bool(overrides[key])

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


def _format_span_list(spans: list[float]) -> str:
    return ", ".join(str(int(round(float(s)))) for s in spans)


def format_shed_assembly_context(
    elements: list[ProjectElementMm],
    assembly_id: str = SHED_ASSEMBLY_ID,
) -> str:
    """Inject live shed parameters so the model can mutate x_spans / z_spans arrays."""
    from core.project_session import get_shed_params

    members = shed_members_in(elements, assembly_id)
    if not members:
        return ""

    stored = get_shed_params(assembly_id)
    params: dict[str, Any] = stored or infer_shed_params_from_elements(members)
    x_spans = params.get("x_spans") or []
    z_spans = params.get("z_spans") or []
    x_str = _format_span_list(x_spans) if isinstance(x_spans, list) else str(x_spans)
    z_str = _format_span_list(z_spans) if isinstance(z_spans, list) else str(z_spans)

    return (
        f"\n---\nACTIVE SHED ASSEMBLY ({assembly_id}) — "
        f"MUST call modify_shed_assembly for any layout or parameter change:\n"
        f"- x_spans (mm, comma-separated): \"{x_str}\" → width {int(params.get('width', 0))} mm (X axis)\n"
        f"- z_spans (mm, comma-separated): \"{z_str}\" → length {int(params.get('length', 0))} mm (+Z / building depth)\n"
        f"- height (mm): {int(params.get('height', 0))}\n"
        f"- roof_style: {params.get('roof_style', 'duo_pitch')}\n"
        f"- roof_pitch_deg: {params.get('roof_pitch_deg', 10)}\n"
        f"- use_truss: {params.get('use_truss', False)}, use_bracing: {params.get('use_bracing', False)}, "
        f"use_sag_rods: {params.get('use_sag_rods', False)}\n"
        f"- generate_wall_girts: {params.get('generate_wall_girts', True)}, "
        f"generate_tie_beams: {params.get('generate_tie_beams', True)}\n"
        f"\nArray mutation rules (pass FULL updated strings in modify_shed_assembly):\n"
        f"- Add one Z bay (e.g. user: \"add a bay to the right\"): append the new bay width to z_spans.\n"
        f"  Example: current \"{z_str}\" + 5000 mm bay → \"{z_str}, 5000\" (if first bay is 5000 mm).\n"
        f"- Add X bay (wider building): append to x_spans the same way.\n"
        f"- Pitch / style: set roof_pitch_deg or roof_style only; keep other fields null.\n"
        f"- NEVER describe geometry changes in prose without calling modify_shed_assembly.\n"
    )

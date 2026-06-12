"""Deterministic surgical edits on an existing project model."""

from __future__ import annotations

import math
import re
from typing import Iterable, Literal

from catalog_loader import get_profile, has_profile
from core.geometry_engine import macro_member_to_project_element
from core.ground_placement import (
    collect_ground_placement_nodes,
    structural_member_for_column,
)
from core.member_resolver import member_from_grid_nodes
from core.spatial_grid import StructuralGridEngine
from schemas.elements import ProjectElementMm, SectionDimensionsMm
from schemas.model_edit import GridPlacementContext
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralMember

_AXIS_SAFE_RE = re.compile(r"[^A-Za-z0-9]+")

_BRACE_PAIR_RE = re.compile(r"^(?P<prefix>.+)-([ab])$", re.IGNORECASE)
_BRACE_CUSTOM_IDX_RE = re.compile(r"-brace-custom-(\d+)-[ab]$", re.IGNORECASE)

_ENDPOINT_ROUND_MM = 1.0
_MIN_MEMBER_LENGTH_MM = 50.0


def _grid_axis_token(label: str) -> str:
    """Safe token for element ids (fractional grid refs like 2+4/120)."""
    return str(label).strip().replace("+", "p").replace("/", "_")


def _brace_pair_prefix(element_id: str) -> str | None:
    match = _BRACE_PAIR_RE.match(element_id)
    if not match:
        return None
    return match.group("prefix")


def _brace_pair_ids(element_id: str) -> tuple[str, str] | None:
    prefix = _brace_pair_prefix(element_id)
    if not prefix:
        return None
    return f"{prefix}-a", f"{prefix}-b"


_COL_RE = re.compile(r"^.+-col-[A-Z]+-(?P<z>\d+)$")
_RAFTER_RE = re.compile(r"^.+-rafter(?:-(?:L|R))?-(?P<z>\d+)$")
_TRUSS_RE = re.compile(r"^.+-truss-(?:TC|BC|web|post)-(?P<z>\d+)(?:-|$)")
_HAUNCH_RE = re.compile(r"^.+-haunch-(?P<z>\d+)-")


def _frame_z_from_id(element_id: str) -> str | None:
    for pattern in (_COL_RE, _RAFTER_RE, _TRUSS_RE, _HAUNCH_RE):
        match = pattern.match(element_id)
        if match:
            return match.group("z")
    return None


def _matches_frame(element: ProjectElementMm, frame_z: str) -> bool:
    z = _frame_z_from_id(element.id)
    if z == frame_z:
        return True
    return element.id.endswith(f"-{frame_z}") or f"-{frame_z}-" in element.id


def _is_truss_member(element: ProjectElementMm) -> bool:
    et = element.element_type or ""
    if et in ("truss_chord", "truss_web"):
        return True
    return bool(_TRUSS_RE.match(element.id))


def _bracing_group_key(element: ProjectElementMm) -> str | None:
    if element.element_type not in ("bracing", "x_brace"):
        if "-brace-" not in element.id:
            return None
    et = element.element_type or "bracing"
    if "-brace-roof-" in element.id:
        return "roof_bracing"
    if "-brace-end-" in element.id:
        return "gable_bracing"
    if re.search(r"-brace-[AB]-", element.id, re.IGNORECASE):
        return "wall_bracing"
    return et


def _resolve_target_ids(
    elements: list[ProjectElementMm],
    *,
    reference_element_id: str | None,
    scope: str,
) -> list[str]:
    if not reference_element_id:
        return []
    ref = next((e for e in elements if e.id == reference_element_id), None)
    if ref is None:
        raise ValueError(f"Element not found: {reference_element_id}")

    if scope == "selection":
        return [reference_element_id]

    if scope == "pair":
        pair = _brace_pair_ids(reference_element_id)
        if pair:
            return [eid for eid in pair if any(e.id == eid for e in elements)]
        return [reference_element_id]

    if scope == "group":
        key = _bracing_group_key(ref)
        if not key:
            return [reference_element_id]
        return [
            e.id
            for e in elements
            if _bracing_group_key(e) == key
        ]

    if scope == "element_type":
        et = ref.element_type or "bracing"
        return [e.id for e in elements if (e.element_type or "") == et]

    if scope == "frame":
        frame_z = _frame_z_from_id(reference_element_id)
        if not frame_z:
            return [reference_element_id]
        return [e.id for e in elements if _matches_frame(e, frame_z)]

    if scope == "truss":
        frame_z = _frame_z_from_id(reference_element_id)
        if not frame_z:
            return [reference_element_id]
        return [
            e.id
            for e in elements
            if _matches_frame(e, frame_z) and _is_truss_member(e)
        ]

    return [reference_element_id]


def _apply_profile_to_element(
    element: ProjectElementMm,
    profile: str,
) -> ProjectElementMm:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    cat = get_profile(profile)
    section = SectionDimensionsMm(
        h=float(cat["h"]),
        b=float(cat["b"]),
        tw=float(cat.get("tw") or 0),
        tf=float(cat.get("tf") or 0),
        t=cat.get("t"),
        d=cat.get("d"),
        ro=cat.get("ro"),
        r=cat.get("r"),
        lip=cat.get("lip"),
    )
    shape = str(cat.get("shape", "Angle"))
    shape_map = {
        "Angle": "Angle",
        "I-beam": "I-beam",
        "RHS": "RHS",
        "SHS": "RHS",
        "CHS": "CHS",
        "Pipe": "Pipe",
        "C-channel": "C-channel",
        "Zed": "Zed",
        "Tee": "Tee",
        "Plate": "Plate",
    }
    return element.model_copy(
        update={
            "profile_name": profile,
            "section_source": "catalog",
            "section_mm": section,
            "shape_type": shape_map.get(shape, element.shape_type),
            "depth_mm": section.h,
            "width_mm": section.b,
        }
    )


def update_member_profiles(
    elements: list[ProjectElementMm],
    *,
    profile: str,
    element_ids: Iterable[str] | None = None,
    reference_element_id: str | None = None,
    scope: str = "selection",
) -> tuple[list[ProjectElementMm], list[str]]:
    if element_ids:
        targets = set(element_ids)
    else:
        targets = set(
            _resolve_target_ids(
                elements,
                reference_element_id=reference_element_id,
                scope=scope,
            )
        )
    if not targets:
        raise ValueError("No target members to update")

    changed: list[str] = []
    out: list[ProjectElementMm] = []
    for element in elements:
        if element.id in targets:
            out.append(_apply_profile_to_element(element, profile))
            changed.append(element.id)
        else:
            out.append(element)
    return out, changed


def delete_members(
    elements: list[ProjectElementMm],
    *,
    element_ids: Iterable[str] | None = None,
    reference_element_id: str | None = None,
    scope: str = "selection",
) -> tuple[list[ProjectElementMm], list[str]]:
    if element_ids:
        targets = set(element_ids)
    else:
        targets = set(
            _resolve_target_ids(
                elements,
                reference_element_id=reference_element_id,
                scope=scope,
            )
        )
    if not targets:
        raise ValueError("No target members to delete")
    remaining = [e for e in elements if e.id not in targets]
    return remaining, sorted(targets)


def _next_brace_index(elements: list[ProjectElementMm], assembly_id: str) -> int:
    max_idx = 0
    for element in elements:
        if element.assembly_id != assembly_id:
            continue
        match = _BRACE_CUSTOM_IDX_RE.search(element.id)
        if match:
            max_idx = max(max_idx, int(match.group(1)))
    return max_idx + 1


def _dedupe_elements_by_id(
    elements: list[ProjectElementMm],
) -> list[ProjectElementMm]:
    seen: set[str] = set()
    out: list[ProjectElementMm] = []
    for element in elements:
        if element.id in seen:
            continue
        seen.add(element.id)
        out.append(element)
    return out


def _next_sketch_member_index(
    elements: list[ProjectElementMm],
    assembly_id: str,
    element_type: str,
) -> int:
    token = element_type.replace("_", "-")
    count = sum(
        1
        for e in elements
        if e.assembly_id == assembly_id and f"-sketch-{token}-" in e.id
    )
    return count + 1


def _round_point(
    point: tuple[float, float, float],
    *,
    step: float = _ENDPOINT_ROUND_MM,
) -> tuple[float, float, float]:
    return tuple(round(c / step) * step for c in point)


def _span_key(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    a = _round_point(start)
    b = _round_point(end)
    return tuple(sorted((a, b)))


def _element_span_key(
    element: ProjectElementMm,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    nodes = element.nodes or {}
    start = nodes.get("start") or nodes.get("bottom")
    end = nodes.get("end") or nodes.get("top")
    if not start or not end or len(start) < 3 or len(end) < 3:
        return None
    return _span_key(
        (float(start[0]), float(start[1]), float(start[2])),
        (float(end[0]), float(end[1]), float(end[2])),
    )


def _remove_members_at_span(
    elements: list[ProjectElementMm],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[list[ProjectElementMm], list[str]]:
    """Drop any member already occupying the same start/end nodes (any type)."""
    key = _span_key(start, end)
    removed: list[str] = []
    out: list[ProjectElementMm] = []
    for element in elements:
        el_key = _element_span_key(element)
        if el_key == key:
            removed.append(element.id)
        else:
            out.append(element)
    return out, removed


def _insert_member_replace_by_span(
    elements: list[ProjectElementMm],
    new_el: ProjectElementMm,
    *,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[list[ProjectElementMm], list[str]]:
    out, removed = _remove_members_at_span(elements, start, end)
    out.append(new_el)
    return out, removed + [new_el.id]


def _member_between_points(
    *,
    element_id: str,
    assembly_id: str,
    profile: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    element_type: str = "bracing",
) -> ProjectElementMm:
    dummy = GridNodeReference(x_axis="A", z_axis="1", elevation="ground")
    member = StructuralMember(
        id=element_id,
        element_type=element_type,  # type: ignore[arg-type]
        profile=profile,
        start_node=dummy,
        end_node=dummy,
    )
    macro = member_from_grid_nodes(
        member,
        assembly_id=assembly_id,
        start=start,
        end=end,
        grid=None,
    )
    if macro is None:
        raise ValueError("Brace length too short")
    return macro_member_to_project_element(macro)


def place_member_between_points(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
    element_type: str = "bracing",
) -> tuple[list[ProjectElementMm], list[str]]:
    ref = elements[0] if elements else None
    aid = assembly_id or (ref.assembly_id if ref else None) or "shed_1"
    defaults = {
        "bracing": "L70x70x7",
        "tie_beam": "IPE200",
        "purlin": "C150x2",
        "beam": "IPE200",
    }
    resolved_type = "tie_beam" if element_type == "beam" else element_type
    prof = profile or defaults.get(element_type, defaults.get(resolved_type, "L70x70x7"))
    if not has_profile(prof):
        prof = "L50x50"
    idx = _next_sketch_member_index(elements, aid, resolved_type)
    token = resolved_type.replace("_", "-")
    eid = f"{aid}-sketch-{token}-{idx}"
    new_el = _member_between_points(
        element_id=eid,
        assembly_id=aid,
        profile=prof,
        start=start_mm,
        end=end_mm,
        element_type=resolved_type,
    )
    return _insert_member_replace_by_span(
        elements,
        new_el,
        start=start_mm,
        end=end_mm,
    )


def place_brace_leg(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    return place_member_between_points(
        elements,
        start_mm=start_mm,
        end_mm=end_mm,
        profile=profile,
        assembly_id=assembly_id,
        element_type="bracing",
    )


def place_bracing_cross(
    elements: list[ProjectElementMm],
    *,
    start_a: tuple[float, float, float],
    end_a: tuple[float, float, float],
    start_b: tuple[float, float, float],
    end_b: tuple[float, float, float],
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    ref = elements[0] if elements else None
    aid = assembly_id or (ref.assembly_id if ref else None) or "shed_1"
    prof = profile or "L70x70x7"
    if not has_profile(prof):
        prof = "L50x50"
    idx = _next_brace_index(elements, aid)
    leg_a = _member_between_points(
        element_id=f"{aid}-brace-custom-{idx}-a",
        assembly_id=aid,
        profile=prof,
        start=start_a,
        end=end_a,
    )
    if _span_key(start_a, end_a) == _span_key(start_b, end_b):
        raise ValueError(
            "X-brace complement matches the sketched leg — pick corners on opposite diagonals."
        )
    leg_b = _member_between_points(
        element_id=f"{aid}-brace-custom-{idx}-b",
        assembly_id=aid,
        profile=prof,
        start=start_b,
        end=end_b,
    )
    out = list(elements)
    removed: list[str] = []
    out, removed_a = _remove_members_at_span(out, start_a, end_a)
    removed.extend(removed_a)
    out, removed_b = _remove_members_at_span(out, start_b, end_b)
    removed.extend(removed_b)
    out.append(leg_a)
    out.append(leg_b)
    changed = list(dict.fromkeys(removed + [leg_a.id, leg_b.id]))
    return _dedupe_elements_by_id(out), changed


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_point(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    return (_lerp(a[0], b[0], t), _lerp(a[1], b[1], t), _lerp(a[2], b[2], t))


def place_bracing_cross_subdivided(
    elements: list[ProjectElementMm],
    *,
    corner_a: tuple[float, float, float],
    corner_b: tuple[float, float, float],
    corner_c: tuple[float, float, float],
    corner_d: tuple[float, float, float],
    brace_count: int = 1,
    subdivision: Literal["vertical", "slope"] = "vertical",
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place one or more X-brace pairs by splitting the panel quadrilateral."""
    count = max(1, min(5, int(brace_count)))
    out = list(elements)
    changed: list[str] = []
    for band in range(count):
        f0 = band / count
        f1 = (band + 1) / count
        if subdivision == "vertical":
            start_a = _lerp_point(corner_a, corner_c, f0)
            start_b = _lerp_point(corner_d, corner_b, f1)
            start_c = _lerp_point(corner_a, corner_c, f1)
            start_d = _lerp_point(corner_d, corner_b, f0)
        else:
            start_a = _lerp_point(corner_a, corner_d, f0)
            start_b = _lerp_point(corner_c, corner_b, f1)
            start_c = _lerp_point(corner_c, corner_b, f0)
            start_d = _lerp_point(corner_a, corner_d, f1)
        if _span_key(start_a, start_b) == _span_key(start_c, start_d):
            continue
        out, band_changed = place_bracing_cross(
            out,
            start_a=start_a,
            end_a=start_b,
            start_b=start_c,
            end_b=start_d,
            profile=profile,
            assembly_id=assembly_id,
        )
        changed.extend(band_changed)
    return out, list(dict.fromkeys(changed))


def place_x_brace_from_leg(
    elements: list[ProjectElementMm],
    *,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    start_element_id: str | None = None,
    end_element_id: str | None = None,
    profile: str | None = None,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    from core.brace_geometry import infer_x_brace_corners

    corners = infer_x_brace_corners(
        start_mm,
        end_mm,
        elements,
        start_element_id=start_element_id,
        end_element_id=end_element_id,
    )
    if corners is None:
        raise ValueError(
            "Could not infer X-brace corners from the sketched leg — try picking grid joints."
        )
    a, b, c, d = corners
    return place_bracing_cross(
        elements,
        start_a=a,
        end_a=b,
        start_b=c,
        end_b=d,
        profile=profile,
        assembly_id=assembly_id,
    )


def _grid_engine_from_context(ctx: GridPlacementContext) -> StructuralGridEngine:
    style = ctx.roof_style if ctx.roof_style in ("duo_pitch", "mono_pitch", "flat") else "duo_pitch"
    pitch = 0.0 if style == "flat" else float(ctx.roof_pitch_deg)
    gd = GridDefinition(
        x_spans=list(ctx.x_spans),
        z_spans=list(ctx.z_spans),
        height_mm=float(ctx.height_mm),
        roof_pitch_deg=pitch,
        roof_style=style,  # type: ignore[arg-type]
        mono_high_side=ctx.mono_high_side if ctx.mono_high_side in ("A", "B") else "B",  # type: ignore[arg-type]
    )
    return StructuralGridEngine.from_definition(gd)


def _infer_assembly_id(elements: list[ProjectElementMm], fallback: str) -> str:
    for element in elements:
        if element.assembly_id:
            return str(element.assembly_id)
    return fallback


def _member_to_element(
    member: StructuralMember,
    *,
    assembly_id: str,
    grid: StructuralGridEngine,
) -> ProjectElementMm:
    start = grid.resolve_node(member.start_node)
    end = grid.resolve_node(member.end_node)
    macro = member_from_grid_nodes(
        member,
        assembly_id=assembly_id,
        start=start,
        end=end,
        grid=grid,
    )
    if macro is None:
        raise ValueError(f"Member {member.id} is too short to place")
    return macro_member_to_project_element(macro)


def _column_x_axis_from_truss(
    engine: StructuralGridEngine,
    *,
    truss_type: str,
    tie_location: str,
    slope_side: str,
) -> str:
    from core.grid_member_catalog import (
        _ridge_label,
        _truss_panel_layout,
        truss_slope_panel_indices,
        truss_tie_panel_index,
    )

    ridge = _ridge_label(engine)
    xlabels, _, _, _ = _truss_panel_layout(engine, ridge, truss_type)
    panel_indices = truss_slope_panel_indices(
        engine,
        truss_type=truss_type,
        slope_side=slope_side,
        ridge_label=ridge,
    )
    panel_i = truss_tie_panel_index(panel_indices, tie_location)
    if panel_i < 0 or panel_i >= len(xlabels):
        raise ValueError(
            f"Truss panel index {panel_i} out of range for column placement."
        )
    return xlabels[panel_i]


def place_grid_column(
    elements: list[ProjectElementMm],
    *,
    x_axis: str,
    z_axis: str,
    profile: str,
    grid: GridPlacementContext,
    trussed_z_labels: Iterable[str] | None = None,
    assembly_id: str | None = None,
    offset_mm: dict[str, float] | None = None,
    connect_to: str = "auto",
    truss_type: str = "pratt",
    add_tie_in_bay: bool = False,
    tie_profile: str | None = None,
    bay_z_start: str | None = None,
    bay_z_end: str | None = None,
    tie_location: str | None = None,
    slope_side: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    engine = _grid_engine_from_context(grid)
    if tie_location and slope_side:
        x = _column_x_axis_from_truss(
            engine,
            truss_type=truss_type,
            tie_location=tie_location,
            slope_side=slope_side,
        )
    else:
        x = x_axis.strip().upper()
        try:
            engine.resolve_x_mm(x)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
    z = z_axis.strip()
    off = dict(offset_mm or {})
    try:
        engine.resolve_z_mm(z)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    trussed = list(trussed_z_labels or [])
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    off_token = ""
    if off:
        off_token = "-o" + _grid_axis_token(
            "_".join(f"{k}{v}" for k, v in sorted(off.items()))
        )
    eid = f"{aid}-col-{x}-{_grid_axis_token(z)}{off_token}"

    member = structural_member_for_column(
        element_id=eid,
        profile=profile,
        x_axis=x,
        z_axis=z,
        offset_mm=off,
        engine=engine,
        trussed_z_labels=trussed,
        truss_type=truss_type,
        connect_to=connect_to,
    )
    new_el = _member_to_element(member, assembly_id=aid, grid=engine)

    out: list[ProjectElementMm] = []
    changed: list[str] = []
    replaced = False
    for element in elements:
        if element.id == eid:
            out.append(new_el)
            replaced = True
            changed.append(eid)
        else:
            out.append(element)
    if not replaced:
        out.append(new_el)
        changed.append(eid)

    if add_tie_in_bay and bay_z_start and bay_z_end:
        tie_prof = tie_profile or "IPE200"
        if has_profile(tie_prof):
            out, tie_ids = place_grid_tie_beam(
                out,
                x_axis=x,
                z_start=bay_z_start,
                z_end=bay_z_end,
                profile=tie_prof,
                grid=grid,
                assembly_id=aid,
            )
            changed.extend(tie_ids)

    return out, changed


def _trussed_frame_z_labels(elements: list[ProjectElementMm]) -> set[str]:
    trussed: set[str] = set()
    for element in elements:
        match = _TRUSS_RE.match(element.id)
        if match:
            trussed.add(match.group("z"))
    return trussed


def _place_roof_x_for_bay(
    elements: list[ProjectElementMm],
    *,
    engine: StructuralGridEngine,
    bay_index: int,
    profile: str | None,
    assembly_id: str,
) -> tuple[list[ProjectElementMm], list[str]]:
    from core.grid_member_catalog import _ridge_label, _roof_bracing

    z_labels = engine.z_labels
    z0 = z_labels[bay_index]
    z1 = z_labels[bay_index + 1]
    trussed = _trussed_frame_z_labels(elements)
    use_truss = z0 in trussed or z1 in trussed
    ridge = _ridge_label(engine)
    members = _roof_bracing(
        engine,
        assembly_id,
        bay_index,
        z0,
        z1,
        ridge,
        profile or "L70x70x7",
        truss_type="pratt",
        use_truss=use_truss,
    )
    out = list(elements)
    changed: list[str] = []
    for i in range(0, len(members), 2):
        if i + 1 >= len(members):
            break
        leg_a, leg_b = members[i], members[i + 1]
        start_a = engine.resolve_node(leg_a.start_node)
        end_a = engine.resolve_node(leg_a.end_node)
        start_b = engine.resolve_node(leg_b.start_node)
        end_b = engine.resolve_node(leg_b.end_node)
        out, cross_changed = place_bracing_cross(
            out,
            start_a=start_a,
            end_a=end_a,
            start_b=start_b,
            end_b=end_b,
            profile=profile,
            assembly_id=assembly_id,
        )
        changed.extend(cross_changed)
    return out, changed


_COL_WALL_RE = re.compile(r"^.+-col-([A-Z]+)-", re.IGNORECASE)
_GABLEPOST_FRAME_RE = re.compile(r"^.+-gablepost-(?P<z>\d+)-", re.IGNORECASE)
_COL_FRAME_RE = re.compile(r"^.+-col-[A-Z]+-(?P<z>\d+)$", re.IGNORECASE)
_COLUMN_CLUSTER_TOL_MM = 300.0


def _is_column_element(element: ProjectElementMm) -> bool:
    et = (element.element_type or "").lower()
    if et == "column":
        return True
    return "-col-" in element.id.lower()


def _member_foot_mm(
    element: ProjectElementMm,
) -> tuple[float, float, float] | None:
    nodes = element.nodes or {}
    start = nodes.get("start") or nodes.get("bottom")
    end = nodes.get("end") or nodes.get("top")
    if not start or not end or len(start) < 3 or len(end) < 3:
        return None
    if start[1] <= end[1]:
        return (float(start[0]), float(start[1]), float(start[2]))
    return (float(end[0]), float(end[1]), float(end[2]))


def _cluster_sorted_mm(values: list[float], tol: float = _COLUMN_CLUSTER_TOL_MM) -> list[float]:
    sorted_vals = sorted(values)
    out: list[float] = []
    for value in sorted_vals:
        if not out or value - out[-1] > tol:
            out.append(value)
    return out


def _long_wall_column_z_mm(elements: list[ProjectElementMm], wall_x: str) -> list[float]:
    wall = wall_x.strip().upper()
    z_values: list[float] = []
    for element in elements:
        if not _is_column_element(element):
            continue
        match = _COL_WALL_RE.match(element.id)
        if not match or match.group(1).upper() != wall:
            continue
        foot = _member_foot_mm(element)
        if foot is not None:
            z_values.append(foot[2])
    return _cluster_sorted_mm(z_values)


def _gable_vertical_x_mm(elements: list[ProjectElementMm], frame_z: str) -> list[float]:
    frame = frame_z.strip()
    x_values: list[float] = []
    for element in elements:
        is_gable_post = "-gablepost-" in element.id.lower()
        is_col = _is_column_element(element)
        if not is_gable_post and not is_col:
            continue
        frame_match = False
        if is_gable_post:
            match = _GABLEPOST_FRAME_RE.match(element.id)
            frame_match = bool(match and match.group("z") == frame)
        else:
            match = _COL_FRAME_RE.match(element.id)
            frame_match = bool(match and match.group("z") == frame)
        if not frame_match:
            continue
        foot = _member_foot_mm(element)
        if foot is not None:
            x_values.append(foot[0])
    return _cluster_sorted_mm(x_values)


def _long_wall_bays_from_columns(
    elements: list[ProjectElementMm],
    wall_x: str,
    engine: StructuralGridEngine,
) -> list[tuple[str, str]]:
    from core.grid_member_catalog import _distinct_refs_at_mm

    z_positions = _long_wall_column_z_mm(elements, wall_x)
    bays: list[tuple[str, str]] = []
    for idx in range(len(z_positions) - 1):
        z0 = z_positions[idx]
        z1 = z_positions[idx + 1]
        if abs(z1 - z0) < 1.0:
            continue
        zs, ze = _distinct_refs_at_mm(engine, z0, z1, "z")
        bays.append((zs, ze))
    return bays


def _long_wall_bays_in_z_range(
    elements: list[ProjectElementMm],
    wall_x: str,
    engine: StructuralGridEngine,
    z0_mm: float,
    z1_mm: float,
) -> list[tuple[str, str]]:
    """Column-pair bays on one side wall overlapping a frame Z span."""
    from core.grid_member_catalog import _distinct_refs_at_mm

    z_lo = min(z0_mm, z1_mm)
    z_hi = max(z0_mm, z1_mm)
    z_positions = _long_wall_column_z_mm(elements, wall_x)
    bays: list[tuple[str, str]] = []
    for idx in range(len(z_positions) - 1):
        col_z0 = z_positions[idx]
        col_z1 = z_positions[idx + 1]
        if col_z1 <= z_lo + 1.0 or col_z0 >= z_hi - 1.0:
            continue
        if abs(col_z1 - col_z0) < 1.0:
            continue
        zs, ze = _distinct_refs_at_mm(engine, col_z0, col_z1, "z")
        bays.append((zs, ze))
    return bays


def _corners_for_roof_segment(
    engine: StructuralGridEngine,
    x_left: str,
    elev_left: str,
    x_right: str,
    elev_right: str,
    z0: str,
    z1: str,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    a = engine.resolve_node(
        GridNodeReference(x_axis=x_left, z_axis=z0, elevation=elev_left)
    )
    b = engine.resolve_node(
        GridNodeReference(x_axis=x_right, z_axis=z1, elevation=elev_right)
    )
    c = engine.resolve_node(
        GridNodeReference(x_axis=x_left, z_axis=z1, elevation=elev_left)
    )
    d = engine.resolve_node(
        GridNodeReference(x_axis=x_right, z_axis=z0, elevation=elev_right)
    )
    return a, b, c, d


def _place_roof_x_at_frame_bay(
    elements: list[ProjectElementMm],
    out: list[ProjectElementMm],
    *,
    engine: StructuralGridEngine,
    z0_label: str,
    z1_label: str,
    brace_count: int,
    profile: str | None,
    assembly_id: str,
) -> tuple[list[ProjectElementMm], list[str]]:
    changed: list[str] = []
    for _side, xa, ea, xb, eb in _roof_slope_panel_defs(engine):
        a, b, c, d = _corners_for_roof_segment(
            engine, xa, ea, xb, eb, z0_label, z1_label
        )
        out, seg_changed = place_bracing_cross_subdivided(
            out,
            corner_a=a,
            corner_b=b,
            corner_c=c,
            corner_d=d,
            brace_count=brace_count,
            subdivision="slope",
            profile=profile,
            assembly_id=assembly_id,
        )
        changed.extend(seg_changed)
    return out, changed


def _place_side_wall_portal_x(
    elements: list[ProjectElementMm],
    out: list[ProjectElementMm],
    *,
    engine: StructuralGridEngine,
    z0_label: str,
    z1_label: str,
    brace_count: int,
    profile: str | None,
    assembly_id: str,
) -> tuple[list[ProjectElementMm], list[str]]:
    """X-brace every column bay on both side walls within a frame Z span."""
    from core.grid_member_catalog import _column_top_elev

    z0_mm = engine.resolve_z_mm(z0_label)
    z1_mm = engine.resolve_z_mm(z1_label)
    changed: list[str] = []
    for wall_label in (engine.x_labels[0], engine.x_labels[-1]):
        column_bays = _long_wall_bays_in_z_range(
            elements, wall_label, engine, z0_mm, z1_mm
        )
        bay_refs = column_bays if column_bays else [(z0_label, z1_label)]
        top = _column_top_elev(engine, wall_label)
        for zs, ze in bay_refs:
            a = engine.resolve_node(
                GridNodeReference(x_axis=wall_label, z_axis=zs, elevation="ground")
            )
            b = engine.resolve_node(
                GridNodeReference(x_axis=wall_label, z_axis=ze, elevation=top)
            )
            c = engine.resolve_node(
                GridNodeReference(x_axis=wall_label, z_axis=zs, elevation=top)
            )
            d = engine.resolve_node(
                GridNodeReference(x_axis=wall_label, z_axis=ze, elevation="ground")
            )
            out, wall_changed = place_bracing_cross_subdivided(
                out,
                corner_a=a,
                corner_b=b,
                corner_c=c,
                corner_d=d,
                brace_count=brace_count,
                subdivision="vertical",
                profile=profile,
                assembly_id=assembly_id,
            )
            changed.extend(wall_changed)
    return out, changed


def _gable_x_bays_from_columns(
    elements: list[ProjectElementMm],
    frame_z: str,
    engine: StructuralGridEngine,
) -> list[tuple[str, str]]:
    from core.grid_member_catalog import _distinct_refs_at_mm

    x_positions = _gable_vertical_x_mm(elements, frame_z)
    bays: list[tuple[str, str]] = []
    for idx in range(len(x_positions) - 1):
        x0 = x_positions[idx]
        x1 = x_positions[idx + 1]
        if abs(x1 - x0) < 1.0:
            continue
        xa, xb = _distinct_refs_at_mm(engine, x0, x1, "x")
        bays.append((xa, xb))
    return bays


def _place_gable_x_brace(
    elements: list[ProjectElementMm],
    *,
    x_bay_index: int,
    frame_z: str,
    x_start: str | None = None,
    x_end: str | None = None,
    profile: str | None = None,
    assembly_id: str | None = None,
    grid: GridPlacementContext,
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel",
    brace_count: int = 1,
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place vertical X-bracing on gable end-wall panel(s) at a fixed Z frame."""
    engine = _grid_engine_from_context(grid)
    x_labels = engine.x_labels
    z_labels = engine.z_labels
    if len(x_labels) < 2:
        raise ValueError("Grid must have at least two X lines for gable bracing")

    z_label = frame_z.strip()
    try:
        engine.resolve_z_mm(z_label)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if z_label not in z_labels:
        raise ValueError(f"Unknown frame {z_label}")

    if x_start and x_end:
        xa = x_start.strip().upper()
        xb = x_end.strip().upper()
    elif 0 <= x_bay_index < len(x_labels) - 1:
        xa = x_labels[x_bay_index]
        xb = x_labels[x_bay_index + 1]
    else:
        raise ValueError(f"Invalid X bay index {x_bay_index}")

    for label in (xa, xb):
        try:
            engine.resolve_x_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    def corners_for_gable(x_left: str, x_right: str, z: str) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        a = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z, elevation="ground")
        )
        b = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z, elevation="eave")
        )
        c = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z, elevation="eave")
        )
        d = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z, elevation="ground")
        )
        return a, b, c, d

    def panels_to_place() -> list[tuple[str, str, str]]:
        near_z, far_z = z_labels[0], z_labels[-1]
        if scope == "this_panel" or scope == "portal_bay":
            return [(xa, xb, z_label)]
        if scope == "parallel_bay":
            other = far_z if z_label == near_z else near_z
            if other == z_label:
                return [(xa, xb, z_label)]
            return list(dict.fromkeys([(xa, xb, z_label), (xa, xb, other)]))
        if scope == "all_bays_wall":
            column_bays = _gable_x_bays_from_columns(elements, z_label, engine)
            if column_bays:
                return [(xa, xb, z_label) for xa, xb in column_bays]
            return [
                (x_labels[bi], x_labels[bi + 1], z_label)
                for bi in range(len(x_labels) - 1)
            ]
        panels: list[tuple[str, str, str]] = []
        for zl in (near_z, far_z):
            column_bays = _gable_x_bays_from_columns(elements, zl, engine)
            if column_bays:
                panels.extend((xa, xb, zl) for xa, xb in column_bays)
            else:
                panels.extend(
                    (x_labels[bi], x_labels[bi + 1], zl)
                    for bi in range(len(x_labels) - 1)
                )
        return panels

    out = list(elements)
    changed: list[str] = []
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    for x_left, x_right, zl in panels_to_place():
        a, b, c, d = corners_for_gable(x_left, x_right, zl)
        out, panel_changed = place_bracing_cross_subdivided(
            out,
            corner_a=a,
            corner_b=b,
            corner_c=c,
            corner_d=d,
            brace_count=brace_count,
            subdivision="vertical",
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(panel_changed)
    if not changed:
        raise ValueError(
            f"Could not place gable bracing at frame {z_label} — "
            "check the selected panel and grid references."
        )
    return out, list(dict.fromkeys(changed))


def _roof_slope_panel_defs(
    engine: StructuralGridEngine,
) -> list[tuple[str, str, str, str, str]]:
    """(slope_side, x_start, elev_start, x_end, elev_end) for each roof slope panel."""
    from core.grid_member_catalog import _ridge_label, _roof_slope_segments

    ridge = _ridge_label(engine)
    segments = _roof_slope_segments(engine, ridge)
    if len(segments) == 1:
        xa, ea, xb, eb = segments[0]
        return [("mono", xa, ea, xb, eb)]
    return [
        ("left", segments[0][0], segments[0][1], segments[0][2], segments[0][3]),
        ("right", segments[1][0], segments[1][1], segments[1][2], segments[1][3]),
    ]


def _place_roof_x_brace(
    elements: list[ProjectElementMm],
    *,
    bay_index: int,
    x_start: str | None,
    x_end: str | None,
    elev_start: str | None,
    elev_end: str | None,
    slope_side: str | None,
    z_start: str | None = None,
    z_end: str | None = None,
    profile: str | None = None,
    assembly_id: str | None = None,
    grid: GridPlacementContext,
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel",
    brace_count: int = 1,
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place X-bracing in one roof slope panel between adjacent frames."""
    engine = _grid_engine_from_context(grid)
    z_labels = engine.z_labels
    if len(z_labels) < 2:
        raise ValueError("Grid must have at least two frames for roof bracing")

    if z_start and z_end:
        z0_label = z_start.strip()
        z1_label = z_end.strip()
    elif 0 <= bay_index < len(z_labels) - 1:
        z0_label = z_labels[bay_index]
        z1_label = z_labels[bay_index + 1]
    else:
        raise ValueError(f"Invalid bay_index {bay_index}")

    if not (x_start and x_end and elev_start and elev_end):
        raise ValueError(
            "Roof bracing requires x_start, x_end, elev_start, and elev_end."
        )

    xa = x_start.strip().upper()
    xb = x_end.strip().upper()
    ea = elev_start.strip().lower()
    eb = elev_end.strip().lower()
    for label in (xa, xb):
        try:
            engine.resolve_x_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
    for label in (z0_label, z1_label):
        try:
            engine.resolve_z_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    z0_mm = engine.resolve_z_mm(z0_label)
    z1_mm = engine.resolve_z_mm(z1_label)
    if abs(z0_mm - z1_mm) < 1.0:
        raise ValueError(
            "Selected roof panel has zero frame-bay width — check grid references."
        )

    slope_defs = _roof_slope_panel_defs(engine)
    primary = next(
        (
            seg
            for seg in slope_defs
            if seg[1] == xa and seg[2] == ea and seg[3] == xb and seg[4] == eb
        ),
        None,
    )
    if primary is None and slope_side:
        primary = next(
            (seg for seg in slope_defs if seg[0] == slope_side.strip().lower()),
            None,
        )
    if primary is None:
        raise ValueError("Unknown roof slope panel — check slope references.")

    def corners_for_roof_panel(
        z0: str,
        z1: str,
        x_left: str,
        elev_left: str,
        x_right: str,
        elev_right: str,
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        a = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z0, elevation=elev_left)
        )
        b = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z1, elevation=elev_right)
        )
        c = engine.resolve_node(
            GridNodeReference(x_axis=x_left, z_axis=z1, elevation=elev_left)
        )
        d = engine.resolve_node(
            GridNodeReference(x_axis=x_right, z_axis=z0, elevation=elev_right)
        )
        return a, b, c, d

    def panels_to_place() -> list[tuple[str, str, str, str, str, str]]:
        z_pairs = [(z0_label, z1_label)]
        if scope == "all_bays_wall":
            z_pairs = [
                (z_labels[i], z_labels[i + 1]) for i in range(len(z_labels) - 1)
            ]

        segments = [primary]
        if scope == "parallel_bay":
            other = next((seg for seg in slope_defs if seg[0] != primary[0]), None)
            if other:
                segments = [primary, other]
        elif scope == "portal_bay":
            segments = slope_defs

        return [
            (z0, z1, seg[1], seg[2], seg[3], seg[4])
            for z0, z1 in z_pairs
            for seg in segments
        ]

    out = list(elements)
    changed: list[str] = []
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    for z0, z1, x_left, elev_left, x_right, elev_right in panels_to_place():
        a, b, c, d = corners_for_roof_panel(
            z0, z1, x_left, elev_left, x_right, elev_right
        )
        out, panel_changed = place_bracing_cross_subdivided(
            out,
            corner_a=a,
            corner_b=b,
            corner_c=c,
            corner_d=d,
            brace_count=brace_count,
            subdivision="slope",
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(panel_changed)
    if scope == "portal_bay":
        out, wall_changed = _place_side_wall_portal_x(
            elements,
            out,
            engine=engine,
            z0_label=z0_label,
            z1_label=z1_label,
            brace_count=brace_count,
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(wall_changed)
    if not changed:
        raise ValueError("Could not place roof bracing — check the selected panel.")
    return out, list(dict.fromkeys(changed))


def place_wall_x_brace(
    elements: list[ProjectElementMm],
    *,
    wall_x: str,
    bay_index: int,
    profile: str | None = None,
    assembly_id: str | None = None,
    grid: GridPlacementContext,
    scope: Literal[
        "this_panel",
        "all_bays_wall",
        "both_walls",
        "parallel_bay",
        "portal_bay",
    ] = "this_panel",
    panel_kind: Literal["long_wall", "gable_wall", "roof"] = "long_wall",
    frame_z: str | None = None,
    z_start: str | None = None,
    z_end: str | None = None,
    x_start: str | None = None,
    x_end: str | None = None,
    elev_start: str | None = None,
    elev_end: str | None = None,
    slope_side: str | None = None,
    brace_count: int = 1,
) -> tuple[list[ProjectElementMm], list[str]]:
    """Place X-bracing on long-side, gable end-wall, or roof slope panel(s)."""
    if panel_kind == "roof":
        return _place_roof_x_brace(
            elements,
            bay_index=bay_index,
            x_start=x_start,
            x_end=x_end,
            elev_start=elev_start,
            elev_end=elev_end,
            slope_side=slope_side,
            z_start=z_start,
            z_end=z_end,
            profile=profile,
            assembly_id=assembly_id,
            grid=grid,
            scope=scope,
            brace_count=brace_count,
        )
    if panel_kind == "gable_wall":
        if not frame_z:
            raise ValueError("frame_z is required for gable wall bracing")
        return _place_gable_x_brace(
            elements,
            x_bay_index=bay_index,
            frame_z=frame_z,
            x_start=x_start,
            x_end=x_end,
            profile=profile,
            assembly_id=assembly_id,
            grid=grid,
            scope=scope,
            brace_count=brace_count,
        )

    from core.grid_member_catalog import _column_top_elev

    engine = _grid_engine_from_context(grid)
    z_labels = engine.z_labels
    x_labels = engine.x_labels
    if len(x_labels) < 2:
        raise ValueError("Grid must have at least two X lines for wall bracing")

    wall = wall_x.strip().upper()
    try:
        engine.resolve_x_mm(wall)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if z_start and z_end:
        z0_label = z_start.strip()
        z1_label = z_end.strip()
    elif 0 <= bay_index < len(z_labels) - 1:
        z0_label = z_labels[bay_index]
        z1_label = z_labels[bay_index + 1]
    else:
        raise ValueError(f"Invalid bay_index {bay_index}")

    for label in (z0_label, z1_label):
        try:
            engine.resolve_z_mm(label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    z0_mm = engine.resolve_z_mm(z0_label)
    z1_mm = engine.resolve_z_mm(z1_label)
    if abs(z0_mm - z1_mm) < 1.0:
        raise ValueError(
            "Selected panel has zero bay width — both columns map to the same grid line."
        )

    def corners_for_bay(
        wall_label: str,
        z0_label: str,
        z1_label: str,
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        top = _column_top_elev(engine, wall_label)
        a = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z0_label, elevation="ground")
        )
        b = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z1_label, elevation=top)
        )
        c = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z0_label, elevation=top)
        )
        d = engine.resolve_node(
            GridNodeReference(x_axis=wall_label, z_axis=z1_label, elevation="ground")
        )
        return a, b, c, d

    def panels_to_place() -> list[tuple[str, str, str]]:
        if scope == "this_panel":
            return [(wall, z0_label, z1_label)]
        if scope == "parallel_bay":
            opposite = (
                x_labels[-1] if wall == x_labels[0] else x_labels[0]
            )
            if opposite == wall:
                return [(wall, z0_label, z1_label)]
            return list(
                dict.fromkeys(
                    [
                        (wall, z0_label, z1_label),
                        (opposite, z0_label, z1_label),
                    ]
                )
            )
        if scope == "portal_bay":
            z0_mm = engine.resolve_z_mm(z0_label)
            z1_mm = engine.resolve_z_mm(z1_label)
            panels: list[tuple[str, str, str]] = []
            for wall_label in (x_labels[0], x_labels[-1]):
                column_bays = _long_wall_bays_in_z_range(
                    elements, wall_label, engine, z0_mm, z1_mm
                )
                if column_bays:
                    panels.extend(
                        (wall_label, zs, ze) for zs, ze in column_bays
                    )
                else:
                    panels.append((wall_label, z0_label, z1_label))
            return panels
        if scope == "all_bays_wall":
            column_bays = _long_wall_bays_from_columns(elements, wall, engine)
            if column_bays:
                return [(wall, zs, ze) for zs, ze in column_bays]
            return [
                (wall, z_labels[bi], z_labels[bi + 1])
                for bi in range(len(z_labels) - 1)
            ]
        side_walls = [x_labels[0], x_labels[-1]]
        column_bays_by_wall = {
            wall_label: _long_wall_bays_from_columns(elements, wall_label, engine)
            for wall_label in side_walls
        }
        if any(column_bays_by_wall.values()):
            return [
                (wall_label, zs, ze)
                for wall_label in side_walls
                for zs, ze in column_bays_by_wall[wall_label]
            ]
        return [
            (wall_label, z_labels[bi], z_labels[bi + 1])
            for wall_label in side_walls
            for bi in range(len(z_labels) - 1)
        ]

    out = list(elements)
    changed: list[str] = []
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    for wall_label, zs, ze in panels_to_place():
        a, b, c, d = corners_for_bay(wall_label, zs, ze)
        out, panel_changed = place_bracing_cross_subdivided(
            out,
            corner_a=a,
            corner_b=b,
            corner_c=c,
            corner_d=d,
            brace_count=brace_count,
            subdivision="vertical",
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(panel_changed)
    if scope == "portal_bay":
        out, roof_changed = _place_roof_x_at_frame_bay(
            elements,
            out,
            engine=engine,
            z0_label=z0_label,
            z1_label=z1_label,
            brace_count=brace_count,
            profile=profile,
            assembly_id=aid,
        )
        changed.extend(roof_changed)
    return out, list(dict.fromkeys(changed))


def place_grid_tie_beam(
    elements: list[ProjectElementMm],
    *,
    x_axis: str = "",
    z_start: str = "",
    z_end: str = "",
    orientation: Literal["along_z", "along_x"] = "along_z",
    z_axis: str | None = None,
    x_start: str | None = None,
    x_end: str | None = None,
    profile: str,
    elevation: str = "eave",
    placement_label: str | None = None,
    truss_chord: Literal["tc", "bc"] | None = None,
    truss_type: str = "pratt",
    slope_side: str | None = None,
    tie_location: str | None = None,
    grid: GridPlacementContext,
    assembly_id: str | None = None,
) -> tuple[list[ProjectElementMm], list[str]]:
    if not has_profile(profile):
        raise ValueError(f"Unknown profile: {profile}")
    engine = _grid_engine_from_context(grid)
    aid = assembly_id or _infer_assembly_id(elements, "shed_1")
    elev = elevation.strip().lower()
    label_suffix = ""
    if placement_label and placement_label.strip():
        label_suffix = f"-{_grid_axis_token(placement_label.strip().lower())}"

    if orientation == "along_x":
        if not z_axis or not x_start or not x_end:
            raise ValueError(
                "Gable tie beam requires z_axis, x_start, and x_end."
            )
        zs = z_axis.strip()
        xa = x_start.strip().upper()
        xb = x_end.strip().upper()
        for label in (xa, xb):
            try:
                engine.resolve_x_mm(label)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        try:
            engine.resolve_z_mm(zs)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        eid = (
            f"{aid}-tie-gable-{_grid_axis_token(zs)}-"
            f"{_grid_axis_token(xa)}-{_grid_axis_token(xb)}-{elev}{label_suffix}"
        )
        start_ref = GridNodeReference(x_axis=xa, z_axis=zs, elevation=elev)
        end_ref = GridNodeReference(x_axis=xb, z_axis=zs, elevation=elev)
    else:
        zs = z_start.strip()
        ze = z_end.strip()
        if not zs or not ze:
            raise ValueError(
                "Tie beam along Z requires z_start and z_end."
            )
        for label in (zs, ze):
            try:
                engine.resolve_z_mm(label)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc

        if truss_chord in ("tc", "bc") and tie_location:
            from core.grid_member_catalog import (
                _ridge_label,
                truss_chord_panel_refs,
                truss_slope_panel_indices,
                truss_tie_panel_index,
            )

            ridge = _ridge_label(engine)
            panel_indices = truss_slope_panel_indices(
                engine,
                truss_type=truss_type,
                slope_side=slope_side,
                ridge_label=ridge,
            )
            panel_i = truss_tie_panel_index(panel_indices, tie_location)
            refs_zs = truss_chord_panel_refs(
                engine,
                zs,
                truss_type=truss_type,
                chord=truss_chord,
                ridge_label=ridge,
            )
            refs_ze = truss_chord_panel_refs(
                engine,
                ze,
                truss_type=truss_type,
                chord=truss_chord,
                ridge_label=ridge,
            )
            if panel_i >= len(refs_zs) or panel_i >= len(refs_ze):
                raise ValueError(
                    f"Truss panel index {panel_i} out of range for {truss_chord} chord."
                )
            start_ref = refs_zs[panel_i]
            end_ref = refs_ze[panel_i]
            x_token = _grid_axis_token(start_ref.x_axis)
            eid = (
                f"{aid}-tie-truss-{truss_chord}-{x_token}-"
                f"{_grid_axis_token(zs)}-{_grid_axis_token(ze)}-p{panel_i}{label_suffix}"
            )
        else:
            x = x_axis.strip().upper()
            if not x:
                raise ValueError(
                    "Tie beam along Z requires x_axis, z_start, and z_end."
                )
            try:
                engine.resolve_x_mm(x)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            eid = (
                f"{aid}-tie-bay-{x}-{_grid_axis_token(zs)}-"
                f"{_grid_axis_token(ze)}-{elev}{label_suffix}"
            )
            start_ref = GridNodeReference(x_axis=x, z_axis=zs, elevation=elev)
            end_ref = GridNodeReference(x_axis=x, z_axis=ze, elevation=elev)
    member = StructuralMember(
        id=eid,
        element_type="tie_beam",
        profile=profile,
        start_node=start_ref,
        end_node=end_ref,
    )
    new_el = _member_to_element(member, assembly_id=aid, grid=engine)
    nodes = new_el.nodes or {}
    start = nodes.get("start")
    end = nodes.get("end")
    if not start or not end:
        raise ValueError("Tie beam nodes missing after placement")
    start_mm = (float(start[0]), float(start[1]), float(start[2]))
    end_mm = (float(end[0]), float(end[1]), float(end[2]))
    return _insert_member_replace_by_span(
        elements,
        new_el,
        start=start_mm,
        end=end_mm,
    )


def collect_snap_nodes(
    elements: list[ProjectElementMm],
    *,
    tolerance_mm: float = 250.0,
) -> list[tuple[str, tuple[float, float, float]]]:
    """Merge connection nodes from all members for viewport snapping."""
    buckets: dict[tuple[int, int, int], tuple[str, tuple[float, float, float]]] = {}
    scale = max(tolerance_mm, 50.0)

    def bucket_key(x: float, y: float, z: float) -> tuple[int, int, int]:
        return (
            round(x / scale),
            round(y / scale),
            round(z / scale),
        )

    for element in elements:
        nodes = element.nodes or {}
        for name, coords in nodes.items():
            if not isinstance(coords, (list, tuple)) or len(coords) < 3:
                continue
            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
            key = bucket_key(x, y, z)
            nid = f"{element.id}:{name}"
            if key not in buckets:
                buckets[key] = (nid, (x, y, z))

    return list(buckets.values())

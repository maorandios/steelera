"""Ground-level column placement nodes and truss-aware column tops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.grid_member_catalog import (
    _bay_sag_rows,
    _column_top_for_frame,
    _merge_node_offset,
    _ref,
    _scissor_bottom_chord_y_mm,
    _truss_panel_layout,
)
from core.spatial_grid import StructuralGridEngine
from schemas.model_edit import GridPlacementContext
from schemas.spatial_grid import GridNodeReference, StructuralMember

_WALL_OFFSETS_MM = (600.0, 1200.0, 1800.0, 2400.0)


@dataclass(frozen=True)
class GroundNode:
    id: str
    x: float
    y: float
    z: float
    x_axis: str
    z_axis: str
    offset_mm: dict[str, float]
    label: str
    kind: str
    connect_to: str


def _engine_from_ctx(ctx: GridPlacementContext) -> StructuralGridEngine:
    from core.model_edit import _grid_engine_from_context

    return _grid_engine_from_context(ctx)


def _ridge_label(engine: StructuralGridEngine) -> str | None:
    left, right = engine.x_labels[0], engine.x_labels[-1]
    if engine.roof.is_flat or engine.roof.is_mono or len(engine.x_labels) < 3:
        return None
    for label in engine.x_labels:
        if label not in (left, right):
            return label
    return None


def _node_key(x_axis: str, z_axis: str, offset: dict[str, float]) -> tuple[str, str, tuple[tuple[str, float], ...]]:
    off = tuple(sorted((k, float(v)) for k, v in (offset or {}).items()))
    return (x_axis.strip().upper(), z_axis.strip(), off)


def _add_node(
    out: dict[tuple[str, str, tuple[tuple[str, float], ...]], GroundNode],
    *,
    engine: StructuralGridEngine,
    x_axis: str,
    z_axis: str,
    offset_mm: dict[str, float] | None,
    label: str,
    kind: str,
    connect_to: str,
    node_id: str,
) -> None:
    off = dict(offset_mm or {})
    key = _node_key(x_axis, z_axis, off)
    if key in out:
        return
    ref = GridNodeReference(
        x_axis=x_axis.strip().upper(),
        z_axis=z_axis.strip(),
        elevation="ground",
        offset_mm=off,
    )
    x, y, z = engine.resolve_node(ref)
    out[key] = GroundNode(
        id=node_id,
        x=x,
        y=y,
        z=z,
        x_axis=x_axis.strip().upper(),
        z_axis=z_axis.strip(),
        offset_mm=off,
        label=label,
        kind=kind,
        connect_to=connect_to,
    )


def collect_ground_placement_nodes(
    ctx: GridPlacementContext,
    *,
    trussed_z_labels: Iterable[str] | None = None,
    truss_type: str = "pratt",
    bay_z_start: str | None = None,
    bay_z_end: str | None = None,
    extra_wall_offsets_mm: Iterable[float] | None = None,
) -> list[GroundNode]:
    """Floor dots for column pick mode (primary grid, mid-bay, truss panels, wall offsets)."""
    engine = _engine_from_ctx(ctx)
    trussed = set(trussed_z_labels or [])
    ridge = _ridge_label(engine)
    nodes: dict[tuple[str, str, tuple[tuple[str, float], ...]], GroundNode] = {}

    z_labels = engine.z_labels
    bay_pairs: list[tuple[str, str]] = []
    if bay_z_start and bay_z_end:
        bay_pairs = [(bay_z_start.strip(), bay_z_end.strip())]
    else:
        bay_pairs = [(z_labels[i], z_labels[i + 1]) for i in range(len(z_labels) - 1)]

    wall_offsets = list(extra_wall_offsets_mm or _WALL_OFFSETS_MM)

    for z0, z1 in bay_pairs:
        if z0 not in engine.z_coords_mm or z1 not in engine.z_coords_mm:
            continue
        mid_rows = _bay_sag_rows(engine, z0, z1)
        z_positions = [z0, *mid_rows, z1]

        for x_label in engine.x_labels:
            for z_label in z_positions:
                is_mid = "+" in z_label
                is_truss = z_label.split("+")[0] in trussed or z_label in trussed
                connect = "truss_bc" if is_truss and "+" not in z_label else "eave"
                kind = "mid_bay" if is_mid else "primary"
                _add_node(
                    nodes,
                    engine=engine,
                    x_axis=x_label,
                    z_axis=z_label,
                    offset_mm={},
                    label=f"{x_label} · {z_label}",
                    kind=kind,
                    connect_to=connect,
                    node_id=f"ground-{x_label}-{z_label.replace('+', 'p').replace('/', '_')}",
                )

        for z_label in (z0, z1):
            if z_label not in trussed:
                continue
            xlabels, _, _case, _x_offsets = _truss_panel_layout(
                engine, ridge, truss_type or "pratt"
            )
            for xl in xlabels:
                _add_node(
                    nodes,
                    engine=engine,
                    x_axis=xl,
                    z_axis=z_label,
                    offset_mm={},
                    label=f"Truss panel {xl} · frame {z_label}",
                    kind="truss_panel",
                    connect_to="truss_bc",
                    node_id=f"ground-truss-{xl}-{z_label}",
                )

        left = engine.x_labels[0]
        right = engine.x_labels[-1]
        span_a = engine.x_coords_mm.get(right, 0) - engine.x_coords_mm.get(left, 0)
        for z_label in mid_rows or [f"{z0}+1/2"]:
            for wall in (left, right):
                for dist in wall_offsets:
                    if dist <= 0 or dist >= span_a - 50:
                        continue
                    off_x = float(dist) if wall == left else -float(dist)
                    z_frame = z_label.split("+")[0]
                    _add_node(
                        nodes,
                        engine=engine,
                        x_axis=wall,
                        z_axis=z_label,
                        offset_mm={"x": off_x},
                        label=f"{wall} + {int(dist)} mm · {z_label}",
                        kind="wall_offset",
                        connect_to="truss_bc"
                        if z_frame in trussed
                        else "eave",
                        node_id=f"ground-off-{wall}-{int(dist)}-{z_label.replace('+', 'p')}",
                    )

    return sorted(nodes.values(), key=lambda n: (n.z, n.x, n.label))


def column_end_node_for_placement(
    engine: StructuralGridEngine,
    *,
    x_axis: str,
    z_axis: str,
    offset_mm: dict[str, float] | None,
    trussed_z_labels: Iterable[str],
    truss_type: str,
    connect_to: str,
) -> GridNodeReference:
    """Resolve column top node — truss BC seat when applicable."""
    z = z_axis.strip()
    z_frame = z.split("+")[0]
    trussed = set(trussed_z_labels or [])
    off = dict(offset_mm or {})
    mode = (connect_to or "auto").strip().lower()

    use_truss_bc = mode == "truss_bc" or (
        mode == "auto" and z_frame in trussed and "+" not in z
    )

    if use_truss_bc and z_frame in trussed:
        ridge = _ridge_label(engine)
        xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
            engine, ridge, truss_type or "pratt"
        )
        plan_x, _, _ = engine.resolve_node(
            GridNodeReference(
                x_axis=x_axis.strip().upper(),
                z_axis=z,
                elevation="ground",
                offset_mm=off,
            )
        )
        best_xl = min(
            xlabels,
            key=lambda xl: abs(engine.resolve_x_mm(xl) - plan_x),
        )
        idx = xlabels.index(best_xl)
        if case == "scissor":
            eave_y = engine.roof.eave_y
            y_bc = _scissor_bottom_chord_y_mm(
                engine, xlabels, x_offsets, idx, ridge_i or 0
            )
            y_off = y_bc - eave_y
            panel_off = _merge_node_offset(
                {"y": y_off} if y_off > 1.0 else None,
                x_offsets[idx] if idx < len(x_offsets) else None,
            )
            return _ref(best_xl, z_frame, "eave", panel_off or {})
        panel_off = x_offsets[idx] if idx < len(x_offsets) else {}
        return _ref(best_xl, z_frame, "eave", panel_off or {})

    top = _column_top_for_frame(
        engine,
        x_axis.strip().upper(),
        z,
        trussed,
    )
    return GridNodeReference(
        x_axis=x_axis.strip().upper(),
        z_axis=z,
        elevation=top,
        offset_mm=off,
    )


def structural_member_for_column(
    *,
    element_id: str,
    profile: str,
    x_axis: str,
    z_axis: str,
    offset_mm: dict[str, float] | None,
    engine: StructuralGridEngine,
    trussed_z_labels: Iterable[str],
    truss_type: str,
    connect_to: str,
) -> StructuralMember:
    start_ref = GridNodeReference(
        x_axis=x_axis.strip().upper(),
        z_axis=z_axis.strip(),
        elevation="ground",
        offset_mm=dict(offset_mm or {}),
    )
    end_ref = column_end_node_for_placement(
        engine,
        x_axis=x_axis,
        z_axis=z_axis,
        offset_mm=offset_mm,
        trussed_z_labels=trussed_z_labels,
        truss_type=truss_type,
        connect_to=connect_to,
    )
    return StructuralMember(
        id=element_id,
        element_type="column",
        profile=profile,
        start_node=start_ref,
        end_node=end_ref,
    )

"""
Canonical portal-frame shed builder on the universal grid.

Emits grid-referenced StructuralMembers only (no absolute mm, no per-element trig).
One builder, correct geometry: primary frame, real purlins (run along the length and
seated on the rafters), side + gable wall girts, gable posts, real trusses, X-bracing
pairs and sag-rod runs. All coordinates are resolved later by the spatial grid engine.
"""

from __future__ import annotations

import math

from catalog_loader import get_profile
from core import engineering_rules
from core.roof_geometry import roof_elevation_at_x
from core.spatial_grid import StructuralGridEngine
from schemas.shed_assembly_config import ShedAssemblyConfig
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralMember

# Purlin/girt seating (outside column/rafter face, 90° to support) is applied in
# member_resolver via engineering_rules after grid nodes are resolved.
_MAX_DIV_PER_SPAN = 12
# Fly-brace V leg length along the purlin run (Z). ~rafter depth gives ~45° rise
# from rafter bottom flange to purlin bottom at each purlin × frame crossing.
_FLY_BRACE_Z_LEG_MM = 200.0

# Default secondary-steel profiles (overridable per-generation via the config).
DEFAULT_COLUMN_PROFILE = "HEA200"
DEFAULT_TRUSS_CHORD_PROFILE = "IPE200"
DEFAULT_TRUSS_WEB_PROFILE = "L50x50"
DEFAULT_BRACING_PROFILE = "L50x50"
DEFAULT_PURLIN_PROFILE = "C150x2"
DEFAULT_GIRT_PROFILE = "C150x2"
DEFAULT_SAG_ROD_PROFILE = "ROD12"
DEFAULT_BASE_PLATE_PROFILE = "PL20"


def _ref(
    x: str, z: str, elev: str, offset: dict[str, float] | None = None
) -> GridNodeReference:
    return GridNodeReference(x_axis=x, z_axis=z, elevation=elev, offset_mm=offset or {})


def _panel_offsets(count: int) -> list[dict[str, float]]:
    return [{} for _ in range(count)]


def _panel_x_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    x_offsets: list[dict[str, float]],
    i: int,
) -> float:
    off = x_offsets[i] if i < len(x_offsets) else {}
    return grid.resolve_x_mm(xlabels[i]) + float(off.get("x", 0))


def _merge_node_offset(
    base: dict[str, float] | None, extra: dict[str, float]
) -> dict[str, float] | None:
    merged = dict(base or {})
    merged.update(extra)
    return merged or None


def _roof_elev_at(grid: StructuralGridEngine, x_mm: float) -> float:
    return roof_elevation_at_x(x_mm, grid.roof, grid.total_width_mm)


def _is_eave_line(grid: StructuralGridEngine, x_label: str) -> bool:
    x_mm = grid.x_coords_mm[x_label]
    return abs(_roof_elev_at(grid, x_mm) - grid.roof.eave_y) < 1.0


def _all_frames_trussed(
    grid: StructuralGridEngine, trussed_frames: set[str]
) -> bool:
    return bool(grid.z_labels) and len(trussed_frames) >= len(grid.z_labels)


def _is_mono_gable_end_frame(grid: StructuralGridEngine, z_label: str) -> bool:
    """First/last portal frame on a mono-pitch shed (the gable end wall)."""
    if not grid.roof.is_mono or not grid.z_labels:
        return False
    return z_label in (grid.z_labels[0], grid.z_labels[-1])


def _truss_fills_gable_triangle(
    grid: StructuralGridEngine,
    z_label: str,
    trussed_frames: set[str],
) -> bool:
    """Truss in this frame plane replaces raking gable posts (duo apex or mono end)."""
    if z_label not in trussed_frames:
        return False
    if grid.roof.is_mono:
        return _is_mono_gable_end_frame(grid, z_label)
    return True


def _side_wall_girt_top_y(
    grid: StructuralGridEngine,
    x_label: str,
    trussed_frames: set[str],
) -> float:
    """Side-wall girt bands cannot rise above the vertical supports on that wall."""
    roof_top = _roof_elev_at(grid, grid.x_coords_mm[x_label])
    if _all_frames_trussed(grid, trussed_frames):
        return min(roof_top, grid.roof.eave_y)
    return roof_top


def _vertical_top_elev_at_x(grid: StructuralGridEngine, x_ref: str) -> str:
    """Elevation token for a vertical that rises to the local roofline."""
    x_mm = grid.resolve_x_mm(x_ref)
    if abs(_roof_elev_at(grid, x_mm) - grid.roof.eave_y) < 1.0:
        return "eave"
    return "roof"


def _gable_post_top_elev(
    grid: StructuralGridEngine,
    x_label: str,
    z_label: str,
    trussed_frames: set[str],
) -> str:
    """Gable post height: mono gables step with the slope even when trussed."""
    if _truss_fills_gable_triangle(grid, z_label, trussed_frames):
        return "eave"
    return _vertical_top_elev_at_x(grid, x_label)


def _ridge_label(grid: StructuralGridEngine) -> str | None:
    """X reference at the ridge — a real grid line if one lands there, else a sub-node."""
    if grid.roof.is_flat:
        return None
    ridge_x = grid.roof.ridge_x
    for label in grid.x_labels:
        if abs(grid.x_coords_mm[label] - ridge_x) < 1.0:
            return label
    if grid.roof.is_mono:
        return grid.x_labels[-1] if grid.roof.mono_high_side == "B" else grid.x_labels[0]
    if len(grid.x_labels) >= 2:
        mids = grid.subdivide_x(grid.x_labels[0], grid.x_labels[-1], 2)
        return mids[0] if mids else None
    return None


def _roof_x_positions(grid: StructuralGridEngine, spacing_mm: float) -> list[str]:
    """X references across the full width at ~horizontal spacing (girts, gable posts)."""
    labels = grid.x_labels
    positions: list[str] = []
    for li in range(len(labels) - 1):
        left, right = labels[li], labels[li + 1]
        positions.append(left)
        span = grid.x_coords_mm[right] - grid.x_coords_mm[left]
        n = max(1, min(_MAX_DIV_PER_SPAN, round(span / spacing_mm))) if spacing_mm > 0 else 1
        positions.extend(grid.subdivide_x(left, right, n))
    positions.append(labels[-1])
    seen: set[str] = set()
    return [p for p in positions if not (p in seen or seen.add(p))]


def _x_ref_with_offset(
    grid: StructuralGridEngine, x_mm: float
) -> tuple[str, dict[str, float]]:
    """Grid line + mm offset so resolved X matches ``x_mm`` without rounding drift."""
    labels = grid.x_labels
    coords = grid.x_coords_mm
    for lab in labels:
        if abs(coords[lab] - x_mm) < 0.01:
            return lab, {}
    for li in range(len(labels) - 1):
        x0 = coords[labels[li]]
        x1 = coords[labels[li + 1]]
        if x0 - 0.01 <= x_mm <= x1 + 0.01 and x1 - x0 > 1e-6:
            return labels[li], {"x": round(x_mm - x0, 3)}
    if x_mm <= coords[labels[0]]:
        return labels[0], {"x": round(x_mm - coords[labels[0]], 3)}
    return labels[-1], {"x": round(x_mm - coords[labels[-1]], 3)}


def _resolved_purlin_x(
    grid: StructuralGridEngine, x_axis: str, offset: dict[str, float]
) -> float:
    return grid.resolve_x_mm(x_axis) + float(offset.get("x", 0))


def _purlin_placement_refs(
    grid: StructuralGridEngine, spacing_mm: float
) -> list[tuple[str, dict[str, float]]]:
    """Exact X grid refs for roof purlins — slope-spaced with mirrored duo-pitch layout."""
    roof = grid.roof
    w = grid.total_width_mm

    if roof.is_flat or spacing_mm <= 0:
        xs = engineering_rules._roof_flat_x_mm(w, spacing_mm)
    elif roof.is_mono:
        xs = engineering_rules.mono_pitch_purlin_x_mm(
            w, roof.pitch_rad, roof.mono_high_side, spacing_mm
        )
    else:
        xs = engineering_rules.duo_pitch_purlin_x_mm(
            w, roof.ridge_x, roof.pitch_rad, spacing_mm
        )

    seen: set[float] = set()
    refs: list[tuple[str, dict[str, float]]] = []
    for x in sorted(xs):
        key = round(x, 3)
        if key in seen:
            continue
        seen.add(key)
        refs.append(_x_ref_with_offset(grid, x))
    return refs


def _column_top_elev(grid: StructuralGridEngine, x_label: str) -> str:
    return "eave" if _is_eave_line(grid, x_label) else "roof"


def _x_ref_at_mm(grid: StructuralGridEngine, x_mm: float, *, denom: int = 120) -> str:
    """Resolvable X reference for an arbitrary absolute X position.

    Snaps to a grid line when coincident, else expresses the point as a fraction
    of the span it falls in (``A+i/denom``) so the spatial grid can resolve it.
    """
    labels = grid.x_labels
    coords = grid.x_coords_mm
    for lab in labels:
        if abs(coords[lab] - x_mm) < 1.0:
            return lab
    for li in range(len(labels) - 1):
        x0 = coords[labels[li]]
        x1 = coords[labels[li + 1]]
        if x0 - 1.0 <= x_mm <= x1 + 1.0 and x1 - x0 > 1e-6:
            frac = (x_mm - x0) / (x1 - x0)
            i = max(1, min(denom - 1, round(frac * denom)))
            return f"{labels[li]}+{i}/{denom}"
    return labels[0] if x_mm <= coords[labels[0]] else labels[-1]


# --------------------------------------------------------------------------- #
# Individual structural systems                                               #
# --------------------------------------------------------------------------- #


def _column_top_for_frame(
    grid: StructuralGridEngine,
    x_label: str,
    z_label: str,
    trussed_frames: set[str],
) -> str:
    """Column height at one grid intersection."""
    roofline_top = _column_top_elev(grid, x_label)
    if z_label not in trussed_frames:
        return roofline_top
    return "eave"


def _columns(
    grid: StructuralGridEngine,
    aid: str,
    trussed_frames: set[str],
    profile: str = DEFAULT_COLUMN_PROFILE,
) -> list[StructuralMember]:
    """Columns to the level where their roof structure connects.

    Rafter frame: column rises to the roof line at its X (eave on eave walls, apex at
    a ridge/interior line). Truss frame: every column stops at eave — the truss bottom
    chord bears on top (mono gable-end trusses carry the high side in the end-wall plane).
    """
    out: list[StructuralMember] = []
    for x_label in grid.x_labels:
        for z_label in grid.z_labels:
            top = _column_top_for_frame(grid, x_label, z_label, trussed_frames)
            out.append(
                StructuralMember(
                    id=f"{aid}-col-{x_label}-{z_label}",
                    element_type="column",
                    profile=profile,
                    start_node=_ref(x_label, z_label, "ground"),
                    end_node=_ref(x_label, z_label, top),
                )
            )
    return out


def _rafters(
    grid: StructuralGridEngine, aid: str, z_label: str, ridge_label: str | None
) -> list[StructuralMember]:
    left, right = grid.x_labels[0], grid.x_labels[-1]
    if grid.roof.is_mono or len(grid.x_labels) == 1 or ridge_label in (None, left, right):
        lo, hi = (left, right)
        # rafter spans low eave to high roof; for mono the high side may be A.
        start_elev = "eave" if _is_eave_line(grid, lo) else "roof"
        end_elev = "eave" if _is_eave_line(grid, hi) else "roof"
        return [
            StructuralMember(
                id=f"{aid}-rafter-{z_label}",
                element_type="rafter",
                profile="IPE200",
                start_node=_ref(lo, z_label, start_elev),
                end_node=_ref(hi, z_label, end_elev),
            )
        ]
    out: list[StructuralMember] = []
    out.append(
        StructuralMember(
            id=f"{aid}-rafter-L-{z_label}",
            element_type="rafter",
            profile="IPE200",
            start_node=_ref(left, z_label, "eave"),
            end_node=_ref(ridge_label, z_label, "apex"),
        )
    )
    out.append(
        StructuralMember(
            id=f"{aid}-rafter-R-{z_label}",
            element_type="rafter",
            profile="IPE200",
            start_node=_ref(ridge_label, z_label, "apex"),
            end_node=_ref(right, z_label, "eave"),
        )
    )
    return out


def _truss_panel_layout(
    grid: StructuralGridEngine, ridge_label: str | None, truss_type: str
) -> tuple[list[str], int | None, str, list[dict[str, float]]]:
    """Panel-node X references + apex index + profile case for a truss frame.

    case is ``symmetric`` (duo, apex inside), ``mono`` (single slope) or
    ``flat`` (parallel chords). X labels share top/bottom so nodes stay aligned.
    """
    left, right = grid.x_labels[0], grid.x_labels[-1]
    coords = grid.x_coords_mm
    left_x, right_x = coords[left], coords[right]
    eave_y = grid.roof.eave_y

    symmetric = (
        not grid.roof.is_flat
        and not grid.roof.is_mono
        and ridge_label is not None
        and ridge_label not in (left, right)
    )

    if symmetric:
        if truss_type == "fink":
            return _fink_panel_layout(grid)
        if truss_type == "king_post":
            return _king_post_panel_layout(grid)
        if truss_type == "queen_post":
            return _queen_post_panel_layout(grid)
        if truss_type == "scissor":
            return _scissor_panel_layout(grid)
        ridge_x = grid.resolve_x_mm(ridge_label)
        rise = _roof_elev_at(grid, ridge_x) - eave_y
        fixed = engineering_rules.truss_fixed_panels(truss_type)
        half = (
            max(1, fixed // 2)
            if fixed is not None
            else engineering_rules.truss_panel_count(
                ridge_x - left_x, max(rise * 0.5, 600.0), rise
            )
        )
        left_xs = (
            [left]
            + [
                _x_ref_at_mm(grid, left_x + (ridge_x - left_x) * k / half)
                for k in range(1, half)
            ]
            + [ridge_label]
        )
        right_xs = (
            [
                _x_ref_at_mm(grid, ridge_x + (right_x - ridge_x) * k / half)
                for k in range(1, half)
            ]
            + [right]
        )
        xs = left_xs + right_xs
        return xs, half, "symmetric", _panel_offsets(len(xs))

    if not grid.roof.is_flat:
        rise = abs(_roof_elev_at(grid, right_x) - _roof_elev_at(grid, left_x))
        n = engineering_rules.truss_panel_count(
            grid.total_width_mm, max(rise * 0.5, 600.0), rise
        )
        xs = (
            [left]
            + [
                _x_ref_at_mm(grid, left_x + (right_x - left_x) * k / n)
                for k in range(1, n)
            ]
            + [right]
        )
        high_left = _roof_elev_at(grid, left_x) >= _roof_elev_at(grid, right_x)
        return xs, (0 if high_left else n), "mono", _panel_offsets(len(xs))

    depth = max(600.0, grid.total_width_mm / 20.0)
    n = engineering_rules.truss_panel_count(grid.total_width_mm, depth, 0.0)
    xs = (
        [left]
        + [
            _x_ref_at_mm(grid, left_x + (right_x - left_x) * k / n)
            for k in range(1, n)
        ]
        + [right]
    )
    return xs, None, "flat", _panel_offsets(len(xs))


def _king_post_panel_layout(
    grid: StructuralGridEngine,
) -> tuple[list[str], int, str]:
    """King-post panel lines: apex at mid-span, strut nodes from 45° BC-centre geometry."""
    left, right = grid.x_labels[0], grid.x_labels[-1]
    left_x = grid.resolve_x_mm(left)
    right_x = grid.resolve_x_mm(right)
    span = right_x - left_x
    x_strut_l = engineering_rules.king_post_strut_x_mm(grid)
    x_c = left_x + span * 0.5
    x_strut_r = left_x + span - (x_strut_l - left_x)
    xlabels = [
        _x_ref_at_mm(grid, left_x),
        _x_ref_at_mm(grid, x_strut_l),
        _x_ref_at_mm(grid, x_c),
        _x_ref_at_mm(grid, x_strut_r),
        _x_ref_at_mm(grid, right_x),
    ]
    return xlabels, 2, "king_post", _panel_offsets(len(xlabels))


def _queen_post_panel_layout(
    grid: StructuralGridEngine,
) -> tuple[list[str], int, str]:
    """Queen-post panel lines: rafter mids at 1/4 & 3/4, queen posts at 1/3 & 2/3."""
    left, right = grid.x_labels[0], grid.x_labels[-1]
    left_x = grid.resolve_x_mm(left)
    right_x = grid.resolve_x_mm(right)
    span = right_x - left_x
    fracs = (0.0, 0.25, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.75, 1.0)
    xlabels = [_x_ref_at_mm(grid, left_x + span * frac) for frac in fracs]
    return xlabels, 3, "queen_post", _panel_offsets(len(xlabels))


def _scissor_panel_layout(
    grid: StructuralGridEngine,
) -> tuple[list[str], int, str]:
    """Scissor panel lines at purlin-seat X positions plus the roof apex."""
    left, right = grid.x_labels[0], grid.x_labels[-1]
    ridge_x = grid.roof.ridge_x

    spacing = float(getattr(grid.definition, "purlin_spacing_mm", 1200.0) or 1200.0)
    refs: list[tuple[str, dict[str, float]]] = []
    xs: list[float] = []
    seen: set[float] = set()
    for x_axis, offset in _purlin_placement_refs(grid, spacing):
        x = _resolved_purlin_x(grid, x_axis, offset)
        key = round(x, 3)
        if key in seen:
            continue
        seen.add(key)
        xs.append(x)
        refs.append((x_axis, dict(offset)))

    for x in (grid.resolve_x_mm(left), ridge_x, grid.resolve_x_mm(right)):
        key = round(x, 3)
        if key in seen:
            continue
        seen.add(key)
        xs.append(x)
        refs.append(_x_ref_with_offset(grid, x))

    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs = [xs[i] for i in order]
    refs = [refs[i] for i in order]
    xlabels = [r[0] for r in refs]
    x_offsets = [dict(r[1]) for r in refs]
    ridge_i = min(range(len(xs)), key=lambda i: abs(xs[i] - ridge_x))
    return xlabels, ridge_i, "scissor", x_offsets


def _fink_panel_layout(
    grid: StructuralGridEngine,
) -> tuple[list[str], int, str]:
    """Fink-specific panel lines: TC mids at 1/4 & 3/4 span, BC nodes at 1/3 & 2/3."""
    left, right = grid.x_labels[0], grid.x_labels[-1]
    left_x = grid.resolve_x_mm(left)
    right_x = grid.resolve_x_mm(right)
    span = right_x - left_x
    fracs = (0.0, 0.25, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.75, 1.0)
    xlabels = [_x_ref_at_mm(grid, left_x + span * frac) for frac in fracs]
    return xlabels, 3, "fink", _panel_offsets(len(xlabels))


def _full_mono_rise_mm(grid: StructuralGridEngine) -> float:
    """Total roof rise across a mono-pitch span (high eave minus datum)."""
    left_x = grid.resolve_x_mm(grid.x_labels[0])
    right_x = grid.resolve_x_mm(grid.x_labels[-1])
    return max(
        _roof_elev_at(grid, left_x),
        _roof_elev_at(grid, right_x),
    ) - grid.roof.eave_y


def _mono_portal_indices(n: int, mono_high_side: str) -> tuple[int, int]:
    """Return (low_eave_panel_index, high_eave_panel_index) for mono portal ends."""
    if str(mono_high_side).strip().upper() == "A":
        return n, 0
    return 0, n


def _truss_end_heel_rise_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    i: int,
) -> float:
    """Portal end-post height: TC above BC at the eave bearing (fixed, not a panel sample).

    Sampling one panel inward breaks apex trusses (king-post n=2) by lifting the
    eave TC node to ridge height, which flattens the top chord. Use a capped heel
    rise so end posts stay visible without killing roof pitch.
    """
    _ = i
    span = grid.resolve_x_mm(xlabels[-1]) - grid.resolve_x_mm(xlabels[0])
    if span < 1.0:
        return 250.0
    return min(450.0, max(250.0, span * 0.035))


def _symmetric_top_chord_y_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    i: int,
    ridge_i: int,
) -> float:
    """Absolute Y of a duo-pitch TC panel node on straight heel→ridge→heel lines."""
    n = len(xlabels) - 1
    x_mm = grid.resolve_x_mm(xlabels[i])
    x_left = grid.resolve_x_mm(xlabels[0])
    x_ridge = grid.resolve_x_mm(xlabels[ridge_i])
    x_right = grid.resolve_x_mm(xlabels[n])
    y_heel = grid.roof.eave_y + _truss_end_heel_rise_mm(grid, xlabels, 0)
    y_ridge = _roof_elev_at(grid, x_ridge)
    if ridge_i <= 0 or abs(x_ridge - x_left) < 1.0:
        return y_heel
    if i <= ridge_i:
        frac = (x_mm - x_left) / (x_ridge - x_left)
        return y_heel + frac * (y_ridge - y_heel)
    if abs(x_right - x_ridge) < 1.0:
        return y_ridge
    frac = (x_mm - x_ridge) / (x_right - x_ridge)
    return y_ridge + frac * (y_heel - y_ridge)


def _scissor_top_chord_y_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    x_offsets: list[dict[str, float]],
    i: int,
    ridge_i: int,
) -> float:
    """Absolute Y of a scissor top-chord node — heels at column top, slopes to apex."""
    n = len(xlabels) - 1
    x_mm = _panel_x_mm(grid, xlabels, x_offsets, i)
    x_left = _panel_x_mm(grid, xlabels, x_offsets, 0)
    x_ridge = _panel_x_mm(grid, xlabels, x_offsets, ridge_i)
    x_right = _panel_x_mm(grid, xlabels, x_offsets, n)
    y_eave = grid.roof.eave_y
    y_ridge = _roof_elev_at(grid, x_ridge)

    half_left = x_ridge - x_left
    half_right = x_right - x_ridge
    if half_left < 1.0 or half_right < 1.0:
        return y_eave

    if i <= ridge_i:
        return y_eave + (x_mm - x_left) / half_left * (y_ridge - y_eave)
    return y_eave + (x_right - x_mm) / half_right * (y_ridge - y_eave)


def _scissor_bottom_chord_y_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    x_offsets: list[dict[str, float]],
    i: int,
    ridge_i: int,
) -> float:
    """Absolute Y of a scissor bottom-chord node — ceiling pitch is half the roof pitch."""
    n = len(xlabels) - 1
    x_mm = _panel_x_mm(grid, xlabels, x_offsets, i)
    x_left = _panel_x_mm(grid, xlabels, x_offsets, 0)
    x_ridge = _panel_x_mm(grid, xlabels, x_offsets, ridge_i)
    x_right = _panel_x_mm(grid, xlabels, x_offsets, n)
    y_eave = grid.roof.eave_y
    y_top_ridge = _roof_elev_at(grid, x_ridge)

    half_left = x_ridge - x_left
    half_right = x_right - x_ridge
    if half_left < 1.0 or half_right < 1.0:
        return y_eave

    roof_pitch = math.atan2(y_top_ridge - y_eave, half_left)
    ceiling_pitch = engineering_rules.scissor_ceiling_pitch_rad(roof_pitch)

    if i <= ridge_i:
        return y_eave + (x_mm - x_left) * math.tan(ceiling_pitch)
    return y_eave + (x_right - x_mm) * math.tan(ceiling_pitch)


def _mono_top_chord_y_mm(
    grid: StructuralGridEngine,
    xlabels: list[str],
    i: int,
) -> float:
    """Absolute Y of a mono top-chord panel node on one straight sloped line.

    Low portal: eave + fixed heel rise (same rule as duo end posts). High portal:
    natural roof elevation. Interior nodes interpolate linearly so the TC never
    dips below the first panel (which broke the low end post visually).
    """
    n = len(xlabels) - 1
    low_i, high_i = _mono_portal_indices(n, grid.roof.mono_high_side)
    x_low = grid.resolve_x_mm(xlabels[low_i])
    x_high = grid.resolve_x_mm(xlabels[high_i])
    y_low = grid.roof.eave_y + _truss_end_heel_rise_mm(grid, xlabels, low_i)
    y_high = _roof_elev_at(grid, x_high)
    x_mm = grid.resolve_x_mm(xlabels[i])
    if abs(x_high - x_low) < 1.0:
        return y_low
    frac = (x_mm - x_low) / (x_high - x_low)
    return y_low + frac * (y_high - y_low)


def _truss_top_node(
    grid: StructuralGridEngine,
    z_label: str,
    xlabels: list[str],
    i: int,
    *,
    case: str,
    ridge_i: int | None,
    x_offsets: list[dict[str, float]] | None = None,
) -> GridNodeReference:
    """Top-chord panel node; portal ends always sit above the bottom chord."""
    n = len(xlabels) - 1
    xl = xlabels[i]
    x_off = (x_offsets or _panel_offsets(len(xlabels)))[i]
    if case == "flat":
        return _ref(xl, z_label, "eave", x_off or None)
    if case in ("symmetric", "fink", "king_post", "queen_post", "scissor") and ridge_i is not None:
        if i == ridge_i:
            return _ref(xl, z_label, "apex", x_off or None)
        if case == "scissor":
            y_mm = _scissor_top_chord_y_mm(
                grid, xlabels, x_offsets or _panel_offsets(len(xlabels)), i, ridge_i
            )
        else:
            y_mm = _symmetric_top_chord_y_mm(grid, xlabels, i, ridge_i)
        return _ref(
            xl,
            z_label,
            "eave",
            _merge_node_offset({"y": y_mm - grid.roof.eave_y}, x_off),
        )

    if case == "mono":
        y_mm = _mono_top_chord_y_mm(grid, xlabels, i)
        return _ref(xl, z_label, "eave", {"y": y_mm - grid.roof.eave_y})

    x_mm = grid.resolve_x_mm(xl)
    if abs(_roof_elev_at(grid, x_mm) - grid.roof.eave_y) > 1.0:
        return _ref(xl, z_label, "roof")

    if i in (0, n):
        rise = _truss_end_heel_rise_mm(grid, xlabels, i)
        if rise > 1.0:
            return _ref(xl, z_label, "eave", {"y": rise})
    return _ref(xl, z_label, "roof")


def _truss_top_chord_panel_xy(
    grid: StructuralGridEngine,
    *,
    truss_type: str = "pratt",
) -> tuple[list[float], list[float]]:
    """Resolved top-chord panel node coordinates for one portal frame."""
    ridge = _ridge_label(grid)
    z_label = grid.z_labels[0] if grid.z_labels else "1"
    if grid.roof.is_mono:
        xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
            grid, ridge, truss_type
        )
        if case != "mono" or len(xlabels) < 2:
            xlabels = [grid.x_labels[0], grid.x_labels[-1]]
            x_offsets = _panel_offsets(len(xlabels))
        ridge_i = (len(xlabels) - 1) if grid.roof.mono_high_side == "B" else 0
    else:
        xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
            grid, ridge, truss_type
        )

    xs: list[float] = []
    ys: list[float] = []
    for i, _xl in enumerate(xlabels):
        ref = _truss_top_node(
            grid,
            z_label,
            xlabels,
            i,
            case=case,
            ridge_i=ridge_i,
            x_offsets=x_offsets,
        )
        px, py, _pz = grid.resolve_node(ref)
        xs.append(px)
        ys.append(py)
    return xs, ys


def truss_top_chord_y_at_x(
    grid: StructuralGridEngine,
    x_mm: float,
    *,
    truss_type: str = "pratt",
) -> float:
    """Top-chord centerline elevation at ``x_mm`` (matches truss frame panel nodes)."""
    xs, ys = _truss_top_chord_panel_xy(grid, truss_type=truss_type)
    if not xs:
        return _roof_elev_at(grid, x_mm)

    if x_mm <= xs[0]:
        return ys[0]
    if x_mm >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        x0, x1 = xs[j], xs[j + 1]
        if x0 <= x_mm <= x1 and abs(x1 - x0) > 1e-6:
            t = (x_mm - x0) / (x1 - x0)
            return ys[j] + t * (ys[j + 1] - ys[j])
    return _roof_elev_at(grid, x_mm)


def truss_pitch_at_x(
    grid: StructuralGridEngine,
    x_mm: float,
    *,
    truss_type: str = "pratt",
) -> tuple[float, float]:
    """Local TC segment (pitch_rad, pitch_sign) at ``x_mm`` for purlin seating."""
    xs, ys = _truss_top_chord_panel_xy(grid, truss_type=truss_type)
    if len(xs) < 2:
        return 0.0, 1.0

    seg = len(xs) - 2
    if x_mm <= xs[0]:
        seg = 0
    elif x_mm >= xs[-1]:
        seg = len(xs) - 2
    else:
        for j in range(len(xs) - 1):
            if xs[j] <= x_mm <= xs[j + 1]:
                seg = j
                break

    dx = xs[seg + 1] - xs[seg]
    dy = ys[seg + 1] - ys[seg]
    if abs(dx) < 1e-6:
        return 0.0, 1.0
    pitch_rad = math.atan2(abs(dy), abs(dx))
    pitch_sign = 1.0 if dy >= 0.0 else -1.0
    return pitch_rad, pitch_sign


def _is_portal_end_vertical_web(
    pair: tuple[tuple[str, int], tuple[str, int]],
    n: int,
    *,
    low_i: int | None = None,
    high_i: int | None = None,
) -> bool:
    """Vertical strut at a portal end connecting TC directly above BC."""
    (sa, ia), (sb, ib) = pair
    if sa != "top" or sb != "bottom" or ia != ib:
        return False
    if low_i is not None and ia == low_i:
        return True
    if high_i is not None and ia == high_i:
        return True
    return ia in (0, n)


def _truss_web_member(
    *,
    aid: str,
    z_label: str,
    pair: tuple[tuple[str, int], tuple[str, int]],
    n: int,
    chord: dict[str, list[GridNodeReference]],
    chord_profile: str,
    web_profile: str,
    member_id: str,
    low_i: int | None = None,
    high_i: int | None = None,
) -> StructuralMember:
    """Panel web; portal-end verticals match bottom-chord profile (not angle webs)."""
    (sa, ia), (sb, ib) = pair
    end_post = _is_portal_end_vertical_web(pair, n, low_i=low_i, high_i=high_i)
    return StructuralMember(
        id=member_id,
        element_type="truss_chord" if end_post else "truss_web",
        profile=chord_profile if end_post else web_profile,
        start_node=chord[sa][ia],
        end_node=chord[sb][ib],
    )


def _append_truss_end_posts(
    out: list[StructuralMember],
    *,
    aid: str,
    z_label: str,
    chord: dict[str, list[GridNodeReference]],
    n: int,
    chord_profile: str,
) -> None:
    """Ensure both portal ends have an explicit vertical between TC and BC."""
    for end_i in (0, n):
        pair: tuple[tuple[str, int], tuple[str, int]] = (
            ("top", end_i),
            ("bottom", end_i),
        )
        out.append(
            _truss_web_member(
                aid=aid,
                z_label=z_label,
                pair=pair,
                n=n,
                chord=chord,
                chord_profile=chord_profile,
                web_profile=DEFAULT_TRUSS_WEB_PROFILE,
                member_id=f"{aid}-truss-post-{z_label}-{end_i}",
            )
        )


def _append_mono_portal_end_posts(
    out: list[StructuralMember],
    *,
    aid: str,
    z_label: str,
    chord: dict[str, list[GridNodeReference]],
    low_i: int,
    high_i: int,
    chord_profile: str,
) -> None:
    """Explicit I-beam end posts at both mono portal ends (TC node → BC node)."""
    for tag, end_i in (("low", low_i), ("high", high_i)):
        out.append(
            StructuralMember(
                id=f"{aid}-truss-post-{z_label}-{tag}",
                element_type="truss_chord",
                profile=chord_profile,
                start_node=chord["top"][end_i],
                end_node=chord["bottom"][end_i],
            )
        )


def _is_mono_portal_end_vertical(
    pair: tuple[tuple[str, int], tuple[str, int]],
    *,
    low_i: int,
    high_i: int,
) -> bool:
    (sa, ia), (sb, ib) = pair
    return sa == "top" and sb == "bottom" and ia == ib and ia in (low_i, high_i)


def _is_eave_portal_end_vertical(
    pair: tuple[tuple[str, int], tuple[str, int]],
    n: int,
) -> bool:
    """Vertical web at a duo/flat portal end (handled by explicit end posts)."""
    (sa, ia), (sb, ib) = pair
    return sa == "top" and sb == "bottom" and ia == ib and ia in (0, n)


def _mono_pitch_truss_frame(
    grid: StructuralGridEngine,
    aid: str,
    z_label: str,
    truss_type: str,
    ridge_label: str | None,
    *,
    chord_profile: str = DEFAULT_TRUSS_CHORD_PROFILE,
    web_profile: str = DEFAULT_TRUSS_WEB_PROFILE,
) -> list[StructuralMember]:
    """Mono-pitch portal truss — flat bottom chord, sloping top chord, panelled webs."""
    xlabels, _ridge_i, case, _x_offsets = _truss_panel_layout(
        grid, ridge_label, truss_type
    )
    if case != "mono" or len(xlabels) < 2:
        xlabels = [grid.x_labels[0], grid.x_labels[-1]]
    n = len(xlabels) - 1

    web_type = truss_type
    if web_type in engineering_rules.APEX_TRUSS_TYPES or web_type == "warren":
        web_type = "pratt"

    ridge_i = n if grid.roof.mono_high_side == "B" else 0
    low_i, high_i = _mono_portal_indices(n, grid.roof.mono_high_side)
    top: list[GridNodeReference] = []
    bottom: list[GridNodeReference] = []
    for i, xl in enumerate(xlabels):
        bottom.append(_ref(xl, z_label, "eave"))
        top.append(
            _truss_top_node(
                grid, z_label, xlabels, i, case="mono", ridge_i=ridge_i
            )
        )

    chord = {"top": top, "bottom": bottom}
    out: list[StructuralMember] = []
    # One continuous top/bottom chord per frame (panel nodes drive webs only).
    for tag, nodes in (("tc", top), ("bc", bottom)):
        out.append(
            StructuralMember(
                id=f"{aid}-truss-{tag}-{z_label}-0",
                element_type="truss_chord",
                profile=chord_profile,
                start_node=nodes[0],
                end_node=nodes[n],
            )
        )

    if web_type == "howe":
        plan = engineering_rules.truss_web_plan("howe", n, ridge_i)
    else:
        plan = engineering_rules.mono_pitch_truss_web_plan(
            n, high_side=grid.roof.mono_high_side
        )

    for k, pair in enumerate(plan):
        if _is_mono_portal_end_vertical(pair, low_i=low_i, high_i=high_i):
            continue
        out.append(
            _truss_web_member(
                aid=aid,
                z_label=z_label,
                pair=pair,
                n=n,
                chord=chord,
                chord_profile=chord_profile,
                web_profile=web_profile,
                member_id=f"{aid}-truss-web-{z_label}-{k}",
                low_i=low_i,
                high_i=high_i,
            )
        )
    _append_mono_portal_end_posts(
        out,
        aid=aid,
        z_label=z_label,
        chord=chord,
        low_i=low_i,
        high_i=high_i,
        chord_profile=chord_profile,
    )
    if web_type == "warren":
        _append_truss_end_posts(
            out,
            aid=aid,
            z_label=z_label,
            chord=chord,
            n=n,
            chord_profile=chord_profile,
        )
    return out


def _truss_frame(
    grid: StructuralGridEngine,
    aid: str,
    z_label: str,
    truss_type: str,
    ridge_label: str | None,
    *,
    chord_profile: str = DEFAULT_TRUSS_CHORD_PROFILE,
    web_profile: str = DEFAULT_TRUSS_WEB_PROFILE,
) -> list[StructuralMember]:
    xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
        grid, ridge_label, truss_type
    )
    n = len(xlabels) - 1
    eave_y = grid.roof.eave_y

    # Apex web patterns require a central node; otherwise fall back to Pratt.
    web_type = truss_type
    if case not in ("symmetric", "fink", "king_post", "queen_post", "scissor") and truss_type in engineering_rules.APEX_TRUSS_TYPES:
        web_type = "pratt"

    flat_depth = max(600.0, grid.total_width_mm / 20.0) if case == "flat" else 0.0

    # Panel-node references — portal ends: TC above BC (explicit end posts).
    top: list[GridNodeReference] = []
    bottom: list[GridNodeReference] = []
    for i, xl in enumerate(xlabels):
        if case == "flat":
            top.append(_ref(xl, z_label, "eave"))
        else:
            top.append(
                _truss_top_node(
                    grid,
                    z_label,
                    xlabels,
                    i,
                    case=case,
                    ridge_i=ridge_i,
                    x_offsets=x_offsets,
                )
            )

        if case == "flat":
            bottom.append(_ref(xl, z_label, "eave", {"y": -flat_depth}))
        elif case == "scissor":
            y_bc = _scissor_bottom_chord_y_mm(
                grid, xlabels, x_offsets, i, ridge_i or 0
            )
            y_off = y_bc - eave_y
            bottom.append(
                _ref(
                    xl,
                    z_label,
                    "eave",
                    _merge_node_offset(
                        {"y": y_off} if y_off > 1.0 else None, x_offsets[i]
                    ),
                )
            )
        else:
            bottom.append(_ref(xl, z_label, "eave"))

    out: list[StructuralMember] = []
    chord = {"top": top, "bottom": bottom}

    # Chords: split at the apex (top) and at the raised centre (scissor bottom).
    top_breaks = [0, ridge_i, n] if case in ("symmetric", "fink", "king_post", "queen_post", "scissor") else [0, n]
    bottom_breaks = [0, ridge_i, n] if case == "scissor" else [0, n]
    for tag, nodes, breaks in (("tc", top, top_breaks), ("bc", bottom, bottom_breaks)):
        for s in range(len(breaks) - 1):
            a, b = breaks[s], breaks[s + 1]
            out.append(
                StructuralMember(
                    id=f"{aid}-truss-{tag}-{z_label}-{s}",
                    element_type="truss_chord",
                    profile=chord_profile,
                    start_node=nodes[a],
                    end_node=nodes[b],
                )
            )

    if case == "scissor" and ridge_i is not None:
        plan = engineering_rules.scissor_truss_web_plan(n, ridge_i)
    else:
        plan = engineering_rules.truss_web_plan(web_type, n, ridge_i)

    allowed_centre = (
        {
            tuple(sorted(p))
            for p in engineering_rules.scissor_centre_web_pairs(ridge_i)
        }
        if case == "scissor" and ridge_i is not None
        else set()
    )
    reserved_centre = (
        engineering_rules.scissor_reserved_endpoints(ridge_i)
        if case == "scissor" and ridge_i is not None
        else frozenset()
    )

    seen_pairs: set[tuple[tuple[str, int], tuple[str, int]]] = set()
    web_k = 0
    for pair in plan:
        if web_type != "warren" and _is_eave_portal_end_vertical(pair, n):
            continue
        if reserved_centre:
            if tuple(sorted(pair)) not in allowed_centre and (
                pair[0] in reserved_centre or pair[1] in reserved_centre
            ):
                continue
        key = tuple(sorted(pair))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        out.append(
            _truss_web_member(
                aid=aid,
                z_label=z_label,
                pair=pair,
                n=n,
                chord=chord,
                chord_profile=chord_profile,
                web_profile=web_profile,
                member_id=f"{aid}-truss-web-{z_label}-{web_k}",
            )
        )
        web_k += 1
    _append_truss_end_posts(
        out,
        aid=aid,
        z_label=z_label,
        chord=chord,
        n=n,
        chord_profile=chord_profile,
    )
    return out


def _truss_top_panel_refs(
    grid: StructuralGridEngine,
    z_label: str,
    ridge_label: str | None,
    truss_type: str,
) -> list[GridNodeReference]:
    """Top-chord panel nodes for one frame (same refs as the frame builder)."""
    if grid.roof.is_mono:
        xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
            grid, ridge_label, truss_type
        )
        if case != "mono" or len(xlabels) < 2:
            xlabels = [grid.x_labels[0], grid.x_labels[-1]]
            x_offsets = _panel_offsets(len(xlabels))
            ridge_i = 1 if grid.roof.mono_high_side == "B" else 0
        return [
            _truss_top_node(
                grid,
                z_label,
                xlabels,
                i,
                case="mono",
                ridge_i=ridge_i,
                x_offsets=x_offsets,
            )
            for i in range(len(xlabels))
        ]

    xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
        grid, ridge_label, truss_type
    )
    return [
        _truss_top_node(
            grid,
            z_label,
            xlabels,
            i,
            case=case,
            ridge_i=ridge_i,
            x_offsets=x_offsets,
        )
        for i in range(len(xlabels))
    ]


def _eave_ridge_ties(
    grid: StructuralGridEngine, aid: str, ridge_label: str | None
) -> list[StructuralMember]:
    z_first, z_last = grid.z_labels[0], grid.z_labels[-1]
    out: list[StructuralMember] = []
    for x_label in (grid.x_labels[0], grid.x_labels[-1]):
        elev = _column_top_elev(grid, x_label)
        out.append(
            StructuralMember(
                id=f"{aid}-tie-{x_label}",
                element_type="tie_beam",
                profile="IPE200",
                start_node=_ref(x_label, z_first, elev),
                end_node=_ref(x_label, z_last, elev),
            )
        )
    if ridge_label is not None and not grid.roof.is_flat:
        out.append(
            StructuralMember(
                id=f"{aid}-tie-ridge",
                element_type="tie_beam",
                profile="IPE200",
                start_node=_ref(ridge_label, z_first, "apex"),
                end_node=_ref(ridge_label, z_last, "apex"),
            )
        )
    return out


def _diaphragm_brace_bays(n_bays: int) -> frozenset[int]:
    """First, middle, and last longitudinal bays (standard diaphragm bracing)."""
    if n_bays <= 0:
        return frozenset()
    if n_bays == 1:
        return frozenset({0})
    bays = {0, n_bays - 1}
    if n_bays >= 3:
        bays.add(n_bays // 2)
    return frozenset(bays)


def _purlins(
    grid: StructuralGridEngine,
    aid: str,
    spacing_mm: float,
    profile: str = DEFAULT_PURLIN_PROFILE,
) -> list[StructuralMember]:
    if spacing_mm <= 0 or len(grid.z_labels) < 2:
        return []
    z_first, z_last = grid.z_labels[0], grid.z_labels[-1]
    # Slope-spaced from each eave; ridge-adjacent pair exactly off the apex.
    placements = _purlin_placement_refs(grid, spacing_mm)
    out: list[StructuralMember] = []
    for i, (xr, off) in enumerate(placements):
        out.append(
            StructuralMember(
                id=f"{aid}-purlin-{i}",
                element_type="purlin",
                profile=profile,
                start_node=_ref(xr, z_first, "roof", off),
                end_node=_ref(xr, z_last, "roof", off),
            )
        )
    return out


def _global_girt_levels(
    eave_y: float,
    apex_y: float,
    spacing_mm: float,
    *,
    wall_level_overrides: dict[str, list[float]] | None = None,
) -> list[float]:
    """Uniform horizontal girt bands around the whole building (default).

    All walls share the same absolute Y levels so girts wrap continuously at corners.
    ``wall_level_overrides`` is reserved for future per-wall UI edits (not used yet).
    """
    _ = wall_level_overrides  # hook for future per-side spacing / level overrides
    if spacing_mm <= 0:
        return []
    levels: list[float] = []
    n_below = max(1, int(eave_y / spacing_mm))
    for i in range(1, n_below + 1):
        levels.append(round(eave_y * i / (n_below + 1), 3))
    levels.append(eave_y)
    y = eave_y + spacing_mm
    while y < apex_y - 1.0:
        levels.append(round(y, 3))
        y += spacing_mm
    return levels


def _girt_nodes_at_y(y_abs: float, eave_y: float) -> tuple[str, dict[str, float] | None]:
    """Express an absolute girt height off the flat eave datum (always horizontal)."""
    if abs(y_abs - eave_y) < 1.0:
        return "eave", None
    return "eave", {"y": y_abs - eave_y}


def _side_wall_girts(
    grid: StructuralGridEngine,
    aid: str,
    levels: list[float],
    profile: str = DEFAULT_GIRT_PROFILE,
    *,
    trussed_frames: set[str] | None = None,
) -> list[StructuralMember]:
    """Horizontal rails on BOTH long side walls at the shared global girt levels."""
    if not levels:
        return []
    z_first, z_last = grid.z_labels[0], grid.z_labels[-1]
    walls = (grid.x_labels[0], grid.x_labels[-1])
    eave_y = grid.roof.eave_y
    trussed = trussed_frames or set()
    out: list[StructuralMember] = []
    for wall in walls:
        top_y = _side_wall_girt_top_y(grid, wall, trussed)
        for li, y_abs in enumerate(levels):
            if y_abs > top_y + 1.0:
                continue
            elev, y_off = _girt_nodes_at_y(y_abs, eave_y)
            out.append(
                StructuralMember(
                    id=f"{aid}-girt-{wall}-L{li}",
                    element_type="wall_girt",
                    profile=profile,
                    start_node=_ref(wall, z_first, elev, y_off),
                    end_node=_ref(wall, z_last, elev, y_off),
                )
            )
    return out


def _gable_posts(
    grid: StructuralGridEngine,
    aid: str,
    spacing_mm: float,
    trussed_frames: set[str],
) -> list[StructuralMember]:
    """End-wall posts between the main columns.

    When a truss fills the gable (duo apex or mono end frame), posts stop at the bottom
    chord. Rafter gables and mono interior frames still use raking posts to the roofline.
    """
    xs = _roof_x_positions(grid, spacing_mm if spacing_mm > 0 else 3000.0)
    main = set(grid.x_labels)
    out: list[StructuralMember] = []
    for z_label in (grid.z_labels[0], grid.z_labels[-1]):
        for i, xr in enumerate(xs):
            if xr in main:
                continue  # main columns already stand on the grid lines
            top = _gable_post_top_elev(grid, xr, z_label, trussed_frames)
            out.append(
                StructuralMember(
                    id=f"{aid}-gablepost-{z_label}-{i}",
                    element_type="column",
                    profile="HEA200",
                    start_node=_ref(xr, z_label, "ground"),
                    end_node=_ref(xr, z_label, top),
                )
            )
    return out


def _gable_girts(
    grid: StructuralGridEngine,
    aid: str,
    levels: list[float],
    post_spacing_mm: float,
    profile: str = DEFAULT_GIRT_PROFILE,
    *,
    trussed_frames: set[str] | None = None,
) -> list[StructuralMember]:
    """Fill END walls at the same global levels as the side walls.

    Girts are never sloped. Each level is one continuous rail from the first to the
    last end-wall support that clears the roof at that height (same as side-wall girts).
    """
    if not levels:
        return []
    xs = _roof_x_positions(grid, post_spacing_mm if post_spacing_mm > 0 else 3000.0)
    if len(xs) < 2:
        return []
    eave_y = grid.roof.eave_y
    roof_at = {x: _roof_elev_at(grid, grid.resolve_x_mm(x)) for x in xs}
    trussed = trussed_frames or set()
    out: list[StructuralMember] = []
    ends = (grid.z_labels[0], grid.z_labels[-1])

    for z_label in ends:
        wall_levels = (
            [y for y in levels if y <= eave_y + 1.0]
            if _truss_fills_gable_triangle(grid, z_label, trussed)
            else levels
        )
        x_first, x_last = grid.x_labels[0], grid.x_labels[-1]
        for li, y_abs in enumerate(wall_levels):
            if (
                roof_at.get(x_first, 0.0) < y_abs - 1.0
                or roof_at.get(x_last, 0.0) < y_abs - 1.0
            ):
                cols = [x for x in xs if roof_at[x] >= y_abs - 1.0]
                if len(cols) < 2:
                    continue
                left, right = cols[0], cols[-1]
            else:
                left, right = x_first, x_last
            elev, y_off = _girt_nodes_at_y(y_abs, eave_y)
            out.append(
                StructuralMember(
                    id=f"{aid}-gablegirt-{z_label}-L{li}",
                    element_type="wall_girt",
                    profile=profile,
                    start_node=_ref(left, z_label, elev, y_off),
                    end_node=_ref(right, z_label, elev, y_off),
                )
            )
    return out


def _cross(
    aid: str,
    tag: str,
    a_start: GridNodeReference,
    a_end: GridNodeReference,
    b_start: GridNodeReference,
    b_end: GridNodeReference,
    *,
    profile: str = "L50x50",
) -> list[StructuralMember]:
    """A diagonal cross (two members) forming an X in any plane."""
    return [
        StructuralMember(
            id=f"{aid}-brace-{tag}-a",
            element_type="bracing",
            profile=profile,
            start_node=a_start,
            end_node=a_end,
        ),
        StructuralMember(
            id=f"{aid}-brace-{tag}-b",
            element_type="bracing",
            profile=profile,
            start_node=b_start,
            end_node=b_end,
        ),
    ]


def _x_bracing(
    grid: StructuralGridEngine,
    aid: str,
    wall: str,
    bay_i: int,
    z0: str,
    z1: str,
    profile: str = DEFAULT_BRACING_PROFILE,
) -> list[StructuralMember]:
    """Vertical cross in a LONG side wall plane (fixed X), across one Z-bay."""
    top = _column_top_elev(grid, wall)
    return _cross(
        aid,
        f"{wall}-b{bay_i}",
        _ref(wall, z0, "ground"),
        _ref(wall, z1, top),
        _ref(wall, z0, top),
        _ref(wall, z1, "ground"),
        profile=profile,
    )


def _end_wall_bracing(
    grid: StructuralGridEngine,
    aid: str,
    post_spacing_mm: float,
    profile: str = DEFAULT_BRACING_PROFILE,
    *,
    trussed_frames: set[str] | None = None,
) -> list[StructuralMember]:
    """Vertical cross in EACH gable END wall plane (fixed Z), in ONE corner bay.

    The X sits between two ADJACENT end-wall columns (corner column → first gable post),
    not stretched across the whole width, and runs ground→eave as a clean rectangular
    panel so it never collides with the sloped roof framing above the eave line.

    Skipped on truss gable frames — the truss itself is the end-wall structure and
    short eave-height X-panels would miss the sloped chords entirely.
    """
    xs = _roof_x_positions(grid, post_spacing_mm if post_spacing_mm > 0 else 3000.0)
    if len(xs) < 2:
        return []
    xa, xb = xs[0], xs[1]
    trussed = trussed_frames or set()
    out: list[StructuralMember] = []
    for z_label in (grid.z_labels[0], grid.z_labels[-1]):
        if z_label in trussed:
            continue
        out.extend(
            _cross(
                aid,
                f"end-{z_label}",
                _ref(xa, z_label, "ground"),
                _ref(xb, z_label, "eave"),
                _ref(xa, z_label, "eave"),
                _ref(xb, z_label, "ground"),
                profile=profile,
            )
        )
    return out


def _roof_slope_segments(
    grid: StructuralGridEngine, ridge_label: str | None
) -> list[tuple[str, str, str, str]]:
    """Roof planes as (x_start, elev_start, x_end, elev_end), mirroring the rafters."""
    left, right = grid.x_labels[0], grid.x_labels[-1]
    if (
        grid.roof.is_mono
        or len(grid.x_labels) == 1
        or ridge_label in (None, left, right)
    ):
        start_elev = "eave" if _is_eave_line(grid, left) else "roof"
        end_elev = "eave" if _is_eave_line(grid, right) else "roof"
        return [(left, start_elev, right, end_elev)]
    return [
        (left, "eave", ridge_label, "apex"),
        (ridge_label, "apex", right, "eave"),
    ]


def _roof_bracing_segments(
    grid: StructuralGridEngine,
    ridge_label: str | None,
    *,
    truss_type: str = "none",
    use_truss: bool = False,
) -> list[tuple[str, str, str, str]]:
    """Roof-plane segments for X-bracing — follow truss top-chord panel lines when trussed."""
    if use_truss and truss_type not in ("none", ""):
        xlabels, _ridge_i, _case, _x_offsets = _truss_panel_layout(
            grid, ridge_label, truss_type
        )
        if len(xlabels) >= 2:
            return [
                (xlabels[i], "roof", xlabels[i + 1], "roof")
                for i in range(len(xlabels) - 1)
            ]
    return _roof_slope_segments(grid, ridge_label)


def _roof_bracing(
    grid: StructuralGridEngine,
    aid: str,
    bay_i: int,
    z0: str,
    z1: str,
    ridge_label: str | None,
    profile: str = DEFAULT_BRACING_PROFILE,
    *,
    truss_type: str = "none",
    use_truss: bool = False,
) -> list[StructuralMember]:
    """Cross bracing in the ROOF planes, tying adjacent frames across one Z-bay.

    Trussed roofs use the exact top-chord panel refs from each frame so diagonals
    land on truss nodes. Rafter roofs follow slope segments in the roof plane.
    """
    out: list[StructuralMember] = []
    if use_truss and truss_type not in ("none", ""):
        top0 = _truss_top_panel_refs(grid, z0, ridge_label, truss_type)
        top1 = _truss_top_panel_refs(grid, z1, ridge_label, truss_type)
        if len(top0) >= 2 and len(top0) == len(top1):
            for s_i in range(len(top0) - 1):
                out.extend(
                    _cross(
                        aid,
                        f"roof-s{s_i}-b{bay_i}",
                        top0[s_i],
                        top1[s_i + 1],
                        top1[s_i],
                        top0[s_i + 1],
                        profile=profile,
                    )
                )
            return out

    segments = _roof_bracing_segments(
        grid, ridge_label, truss_type=truss_type, use_truss=use_truss
    )
    for s_i, (xa, ea, xb, eb) in enumerate(segments):
        out.extend(
            _cross(
                aid,
                f"roof-s{s_i}-b{bay_i}",
                _ref(xa, z0, ea),
                _ref(xb, z1, eb),
                _ref(xa, z1, ea),
                _ref(xb, z0, eb),
                profile=profile,
            )
        )
    return out


def _bay_sag_rows(grid: StructuralGridEngine, z0: str, z1: str) -> list[str]:
    """Mid-bay Z reference rows for sag rods (1 row, or 2 in wide bays)."""
    from core.engineering_rules import sag_rod_bay_fractions

    bay_len = grid.z_coords_mm[z1] - grid.z_coords_mm[z0]
    fracs = sag_rod_bay_fractions(bay_len)
    den = len(fracs) + 1  # 2 → "+1/2"; 3 → "+1/3","+2/3"
    return [f"{z0}+{i}/{den}" for i in range(1, den)]


def _roof_sag_rods(
    grid: StructuralGridEngine,
    aid: str,
    bay_i: int,
    z0: str,
    z1: str,
    purlin_spacing_mm: float,
    profile: str = DEFAULT_SAG_ROD_PROFILE,
) -> list[StructuralMember]:
    """Anti-sag rods between EACH adjacent purlin, in 1-2 rows per bay (LTB control).

    Uses the same X lines as the purlins so the rods actually wire purlin-to-purlin.
    Wide bays (> 5.5 m) get two rows at 1/3 and 2/3; otherwise a single mid-span row.
    """
    placements = _purlin_placement_refs(
        grid, purlin_spacing_mm if purlin_spacing_mm > 0 else 1200.0
    )
    if len(placements) < 2:
        return []
    out: list[StructuralMember] = []
    for r, zr in enumerate(_bay_sag_rows(grid, z0, z1)):
        for k, (left, right) in enumerate(zip(placements, placements[1:])):
            lx, loff = left
            rx, roff = right
            out.append(
                StructuralMember(
                    id=f"{aid}-sag-roof-b{bay_i}-r{r}-{k}",
                    element_type="sag_rod",
                    profile=profile,
                    start_node=_ref(lx, zr, "roof", loff),
                    end_node=_ref(rx, zr, "roof", roff),
                )
            )
    return out


def _long_wall_sag_rods(
    grid: StructuralGridEngine,
    aid: str,
    bay_i: int,
    z0: str,
    z1: str,
    girt_levels: list[float],
    profile: str = DEFAULT_SAG_ROD_PROFILE,
) -> list[StructuralMember]:
    """Anti-sag rods on the LONG side walls, wiring adjacent girts vertically.

    One vertical rod between each pair of adjacent girt levels at 1-2 mid-bay Z rows.
    """
    if len(girt_levels) < 2:
        return []
    eave_y = grid.roof.eave_y
    walls = (grid.x_labels[0], grid.x_labels[-1])
    rows = _bay_sag_rows(grid, z0, z1)
    out: list[StructuralMember] = []
    for wall in walls:
        top_y = _roof_elev_at(grid, grid.x_coords_mm[wall])
        levels = [y for y in girt_levels if y <= top_y + 1.0]
        for r, zr in enumerate(rows):
            for li, (y_lo, y_hi) in enumerate(zip(levels, levels[1:])):
                e_lo, off_lo = _girt_nodes_at_y(y_lo, eave_y)
                e_hi, off_hi = _girt_nodes_at_y(y_hi, eave_y)
                out.append(
                    StructuralMember(
                        id=f"{aid}-sag-wall-{wall}-b{bay_i}-r{r}-{li}",
                        element_type="sag_rod",
                        profile=profile,
                        start_node=_ref(wall, zr, e_lo, off_lo),
                        end_node=_ref(wall, zr, e_hi, off_hi),
                    )
                )
    return out


def _gable_wall_sag_rods(
    grid: StructuralGridEngine,
    aid: str,
    girt_levels: list[float],
    post_spacing_mm: float,
    profile: str = DEFAULT_SAG_ROD_PROFILE,
) -> list[StructuralMember]:
    """Anti-sag rods on the GABLE end walls, wiring adjacent girts vertically.

    One vertical rod per X-bay (between adjacent end-wall columns/posts) at mid-span,
    connecting each pair of adjacent girt levels that fit under the roof at that bay.
    """
    if len(girt_levels) < 2:
        return []
    xs = _roof_x_positions(grid, post_spacing_mm if post_spacing_mm > 0 else 3000.0)
    if len(xs) < 2:
        return []
    eave_y = grid.roof.eave_y
    roof_at = {x: _roof_elev_at(grid, grid.resolve_x_mm(x)) for x in xs}
    out: list[StructuralMember] = []
    for z_label in (grid.z_labels[0], grid.z_labels[-1]):
        for xi, (left, right) in enumerate(zip(xs, xs[1:])):
            x_mid_off = (grid.resolve_x_mm(right) - grid.resolve_x_mm(left)) / 2.0
            bay_top = min(roof_at[left], roof_at[right])
            levels = [y for y in girt_levels if y <= bay_top + 1.0]
            for li, (y_lo, y_hi) in enumerate(zip(levels, levels[1:])):
                e_lo, off_lo = _girt_nodes_at_y(y_lo, eave_y)
                e_hi, off_hi = _girt_nodes_at_y(y_hi, eave_y)
                s_off = dict(off_lo or {})
                e_off = dict(off_hi or {})
                s_off["x"] = x_mid_off
                e_off["x"] = x_mid_off
                out.append(
                    StructuralMember(
                        id=f"{aid}-sag-gable-{z_label}-x{xi}-{li}",
                        element_type="sag_rod",
                        profile=profile,
                        start_node=_ref(left, z_label, e_lo, s_off),
                        end_node=_ref(left, z_label, e_hi, e_off),
                    )
                )
    return out


def _bottom_chord_restraint(
    grid: StructuralGridEngine,
    aid: str,
    trussed_frames: set[str],
    *,
    ridge_label: str | None = None,
    truss_type: str = "none",
) -> list[StructuralMember]:
    """Longitudinal runners restraining truss bottom chords between frames.

    Needs ≥2 trussed frames. Runs along Z at interior panel lines on the actual
    bottom-chord profile (raised for scissor trusses, eave level otherwise).
    """
    z_trussed = [z for z in grid.z_labels if z in trussed_frames]
    if len(z_trussed) < 2:
        return []
    z0, z1 = z_trussed[0], z_trussed[-1]
    out: list[StructuralMember] = []

    if truss_type == "scissor" and not grid.roof.is_flat and not grid.roof.is_mono:
        xlabels, ridge_i, case, x_offsets = _truss_panel_layout(
            grid, ridge_label, truss_type
        )
        if case == "scissor" and len(xlabels) >= 3:
            eave_y = grid.roof.eave_y
            for k, i in enumerate(range(1, len(xlabels) - 1)):
                y_bc = _scissor_bottom_chord_y_mm(
                    grid, xlabels, x_offsets, i, ridge_i or 0
                )
                off = _merge_node_offset(
                    {"y": y_bc - eave_y} if y_bc - eave_y > 1.0 else None,
                    x_offsets[i],
                ) or {}
                out.append(
                    StructuralMember(
                        id=f"{aid}-bctie-{k}",
                        element_type="tie_beam",
                        profile="L50x50",
                        start_node=_ref(xlabels[i], z0, "eave", off),
                        end_node=_ref(xlabels[i], z1, "eave", off),
                    )
                )
            return out

    left_x = grid.x_coords_mm[grid.x_labels[0]]
    right_x = grid.x_coords_mm[grid.x_labels[-1]]
    for k, frac in enumerate((0.25, 0.5, 0.75)):
        xr = _x_ref_at_mm(grid, left_x + (right_x - left_x) * frac)
        out.append(
            StructuralMember(
                id=f"{aid}-bctie-{k}",
                element_type="tie_beam",
                profile="L50x50",
                start_node=_ref(xr, z0, "eave"),
                end_node=_ref(xr, z1, "eave"),
            )
        )
    return out


def _haunches(
    grid: StructuralGridEngine,
    aid: str,
    ridge_label: str | None,
    rafter_frames: list[str],
) -> list[StructuralMember]:
    """Tapered eave (knee) + apex haunches for the rafter (portal) scheme.

    One tapered stub grows INTO each roof-slope segment from every column/apex end,
    deep at the connection and tapering to the rafter depth up-slope. Start node is the
    deep (connection) end; the geometry engine reads the taper from the element type.
    """
    if not rafter_frames:
        return []
    span = grid.total_width_mm
    hlen = min(1500.0, max(600.0, span * 0.1))
    segs = _roof_slope_segments(grid, ridge_label)
    out: list[StructuralMember] = []
    for z_label in rafter_frames:
        for s_i, (xa, _ea, xb, _eb) in enumerate(segs):
            xa_mm = grid.resolve_x_mm(xa)
            xb_mm = grid.resolve_x_mm(xb)
            seglen = abs(xb_mm - xa_mm)
            if seglen < 1.0:
                continue
            h = min(hlen, seglen * 0.4)
            dirx = 1.0 if xb_mm > xa_mm else -1.0
            # Deep at xa → shallow up-slope.
            out.append(
                StructuralMember(
                    id=f"{aid}-haunch-{z_label}-s{s_i}-lo",
                    element_type="haunch",
                    profile="IPE300",
                    start_node=_ref(xa, z_label, "roof"),
                    end_node=_ref(_x_ref_at_mm(grid, xa_mm + dirx * h), z_label, "roof"),
                )
            )
            # Deep at xb → shallow down-slope.
            out.append(
                StructuralMember(
                    id=f"{aid}-haunch-{z_label}-s{s_i}-hi",
                    element_type="haunch",
                    profile="IPE300",
                    start_node=_ref(xb, z_label, "roof"),
                    end_node=_ref(_x_ref_at_mm(grid, xb_mm - dirx * h), z_label, "roof"),
                )
            )
    return out


def _fly_braces(
    grid: StructuralGridEngine,
    aid: str,
    ridge_label: str | None,
    purlin_spacing_mm: float,
    profile: str = DEFAULT_BRACING_PROFILE,
    *,
    trussed_frames: set[str] | None = None,
) -> list[StructuralMember]:
    """Flange braces at every purlin × portal-frame intersection.

    Two per spot form a V in the vertical plane perpendicular to the purlin:
    both legs share the rafter bottom flange at the crossing; each leg runs
    diagonally up along ±Z to the purlin bottom on that side of the web.

    Omitted on trussed frames — there is no rafter flange to brace from.
    """
    _ = ridge_label
    trussed = trussed_frames or set()
    placements = _purlin_placement_refs(
        grid, purlin_spacing_mm if purlin_spacing_mm > 0 else 1200.0
    )
    if not placements:
        return []
    leg_mm = _FLY_BRACE_Z_LEG_MM
    out: list[StructuralMember] = []
    for z_label in grid.z_labels:
        if z_label in trussed:
            continue
        for xi, (xr, off) in enumerate(placements):
            fly_off = dict(off)
            for side, dz in (("L", -leg_mm), ("R", leg_mm)):
                out.append(
                    StructuralMember(
                        id=f"{aid}-fly-{z_label}-x{xi}-{side}",
                        element_type="fly_brace",
                        profile=profile,
                        start_node=_ref(xr, z_label, "roof", fly_off),
                        end_node=_ref(xr, z_label, "roof", {**fly_off, "z": dz}),
                    )
                )
    return out


def _base_plates(
    grid: StructuralGridEngine,
    aid: str,
    gable_post_spacing: float,
    generate_gable: bool,
    profile: str = DEFAULT_BASE_PLATE_PROFILE,
) -> list[StructuralMember]:
    """Square base plates under every column and gable-post foot (at ground level)."""
    half = 180.0
    out: list[StructuralMember] = []

    def _plate(x_label: str, z_label: str, tag: str) -> StructuralMember:
        return StructuralMember(
            id=f"{aid}-baseplate-{tag}",
            element_type="base_plate",
            profile=profile,
            start_node=_ref(x_label, z_label, "ground", {"x": -half}),
            end_node=_ref(x_label, z_label, "ground", {"x": half}),
        )

    for x_label in grid.x_labels:
        for z_label in grid.z_labels:
            out.append(_plate(x_label, z_label, f"{x_label}-{z_label}"))

    if generate_gable:
        xs = _roof_x_positions(grid, gable_post_spacing if gable_post_spacing > 0 else 3000.0)
        main = set(grid.x_labels)
        for z_label in (grid.z_labels[0], grid.z_labels[-1]):
            for i, xr in enumerate(xs):
                if xr in main:
                    continue
                out.append(_plate(xr, z_label, f"gp-{z_label}-{i}"))
    return out


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def members_from_grid_definition(
    grid_def: GridDefinition,
    *,
    assembly_id: str = "shed_1",
) -> list[StructuralMember]:
    """Default complete shed BOM from grid spans + feature flags (no AI member list)."""
    from schemas.shed_assembly_config import (
        ShedAssemblyConfig,
        ShedBayConfiguration,
        ShedGlobalParameters,
        ShedGridLayout,
    )

    n_bays = len(grid_def.z_spans)
    use_truss = bool(getattr(grid_def, "use_truss", False))
    truss_type = getattr(grid_def, "truss_type", "none")
    config = ShedAssemblyConfig(
        assembly_id=assembly_id,
        replace_existing=True,
        global_parameters=ShedGlobalParameters(
            height_mm=grid_def.height_mm,
            roof_pitch_deg=grid_def.roof_pitch_deg,
            roof_style=grid_def.roof_style,
        ),
        grid_layout=ShedGridLayout(
            x_spans=list(grid_def.x_spans),
            z_spans=list(grid_def.z_spans),
        ),
        mono_high_side=getattr(grid_def, "mono_high_side", "B"),
        bays_configuration=[
            ShedBayConfiguration(
                bay_index=i,
                use_truss=use_truss,
                truss_type=truss_type if use_truss else "none",
                x_bracing_left_wall=bool(getattr(grid_def, "x_bracing", False)),
                x_bracing_right_wall=bool(getattr(grid_def, "x_bracing", False)),
                wall_girts=bool(getattr(grid_def, "generate_wall_girts", True)),
                sag_rods=bool(getattr(grid_def, "sag_rods", False)),
            )
            for i in range(n_bays)
        ],
        purlin_spacing_mm=float(getattr(grid_def, "purlin_spacing_mm", 1200.0)),
        girt_spacing_mm=float(getattr(grid_def, "girt_spacing_mm", 1500.0)),
        column_profile=getattr(grid_def, "column_profile", None),
        bracing_profile=getattr(grid_def, "bracing_profile", None),
        purlin_profile=getattr(grid_def, "purlin_profile", None),
        girt_profile=getattr(grid_def, "girt_profile", None),
        sag_rod_profile=getattr(grid_def, "sag_rod_profile", None),
        base_plate_profile=getattr(grid_def, "base_plate_profile", None),
        truss_chord_profile=getattr(grid_def, "truss_chord_profile", None),
        truss_web_profile=getattr(grid_def, "truss_web_profile", None),
        generate_purlins=bool(getattr(grid_def, "generate_purlins", True)),
        generate_tie_beams=bool(getattr(grid_def, "generate_tie_beams", True)),
        gable_bracing=bool(getattr(grid_def, "gable_bracing", False)),
        roof_bracing=bool(getattr(grid_def, "roof_bracing", False)),
        haunches=bool(getattr(grid_def, "haunches", False)),
        fly_braces=bool(getattr(grid_def, "fly_braces", False)),
        base_plates=bool(getattr(grid_def, "base_plates", False)),
        bottom_chord_restraint=bool(getattr(grid_def, "bottom_chord_restraint", False)),
    )
    return members_from_shed_config(
        config, generate_gable=bool(getattr(grid_def, "generate_gable_framing", True))
    )


def members_from_shed_config(
    config: ShedAssemblyConfig, *, generate_gable: bool = True
) -> list[StructuralMember]:
    """Build the full, geometrically correct shed BOM from the parametric config."""
    cfg = config.with_default_bays()
    gp = cfg.global_parameters
    grid_def = GridDefinition(
        x_spans=list(cfg.grid_layout.x_spans),
        z_spans=list(cfg.grid_layout.z_spans),
        height_mm=gp.height_mm,
        roof_pitch_deg=0.0 if gp.roof_style == "flat" else gp.roof_pitch_deg,
        roof_style=gp.roof_style,
        mono_high_side=getattr(cfg, "mono_high_side", "B"),
    )
    grid = StructuralGridEngine.from_definition(grid_def)
    aid = config.assembly_id
    ridge = _ridge_label(grid)
    members: list[StructuralMember] = []

    # Profile choices (fall back to sensible defaults).
    column_profile = getattr(cfg, "column_profile", None) or DEFAULT_COLUMN_PROFILE
    bracing_profile = getattr(cfg, "bracing_profile", None) or DEFAULT_BRACING_PROFILE
    purlin_profile = getattr(cfg, "purlin_profile", None) or DEFAULT_PURLIN_PROFILE
    girt_profile = getattr(cfg, "girt_profile", None) or DEFAULT_GIRT_PROFILE
    sag_rod_profile = getattr(cfg, "sag_rod_profile", None) or DEFAULT_SAG_ROD_PROFILE
    base_plate_profile = (
        getattr(cfg, "base_plate_profile", None) or DEFAULT_BASE_PLATE_PROFILE
    )

    # Determine which frames carry a truss (their columns stop at the bottom chord).
    frame_truss: list[tuple[str, bool, str]] = []
    trussed_frames: set[str] = set()
    for zi, z_label in enumerate(grid.z_labels):
        uses_truss, ttype = cfg.frame_uses_truss(zi)
        frame_truss.append((z_label, uses_truss, ttype))
        if uses_truss:
            trussed_frames.add(z_label)

    rafter_frames = [z for z in grid.z_labels if z not in trussed_frames]
    use_truss = bool(trussed_frames)
    primary_truss_type = next(
        (ttype for _z, uses, ttype in frame_truss if uses),
        "none",
    )

    # Primary frame: columns, then rafters or trusses per frame.
    chord_profile = (
        getattr(cfg, "truss_chord_profile", None) or DEFAULT_TRUSS_CHORD_PROFILE
    )
    web_profile = getattr(cfg, "truss_web_profile", None) or DEFAULT_TRUSS_WEB_PROFILE
    members.extend(_columns(grid, aid, trussed_frames, column_profile))
    for z_label, uses_truss, ttype in frame_truss:
        if uses_truss:
            truss_kw = {
                "chord_profile": chord_profile,
                "web_profile": web_profile,
            }
            if grid.roof.is_mono:
                members.extend(
                    _mono_pitch_truss_frame(
                        grid, aid, z_label, ttype, ridge, **truss_kw
                    )
                )
            else:
                members.extend(
                    _truss_frame(grid, aid, z_label, ttype, ridge, **truss_kw)
                )
        else:
            members.extend(_rafters(grid, aid, z_label, ridge))

    # Tapered eave/apex haunches on rafter (portal) frames.
    if bool(getattr(cfg, "haunches", False)):
        members.extend(_haunches(grid, aid, ridge, rafter_frames))

    # Longitudinal stability: eave/ridge ties tying the frames together.
    if cfg.generate_tie_beams:
        members.extend(_eave_ridge_ties(grid, aid, ridge))

    # Roof purlins (run along the length, seated on the rafters).
    if bool(getattr(cfg, "generate_purlins", True)):
        members.extend(_purlins(grid, aid, cfg.purlin_spacing_mm, purlin_profile))

    # Gable post spacing: ~2x the girt spacing, but fine enough that each roof slope
    # gets at least one intermediate post so horizontal gable girts can step up the
    # slope and fill the gable (a straight girt to a bare ridge post can't rise).
    gable_post_spacing = min(cfg.girt_spacing_mm * 2, max(grid.total_width_mm / 4, 1.0))

    # Wall infill: one shared girt level schedule wraps all walls at the same EL.
    has_wall_girts = any(
        cfg.bay_at(i).wall_girts for i in range(len(grid.z_labels) - 1)
    )
    girt_levels = _global_girt_levels(
        grid.roof.eave_y,
        grid.roof.ridge_y,
        cfg.girt_spacing_mm,
    )
    if has_wall_girts:
        members.extend(
            _side_wall_girts(
                grid, aid, girt_levels, girt_profile, trussed_frames=trussed_frames
            )
        )
        if generate_gable:
            members.extend(
                _gable_girts(
                    grid,
                    aid,
                    girt_levels,
                    gable_post_spacing,
                    girt_profile,
                    trussed_frames=trussed_frames,
                )
            )
    if generate_gable:
        members.extend(_gable_posts(grid, aid, gable_post_spacing, trussed_frames))

    # Per-bay side-wall bracing and sag rods.
    n_bays = len(grid.z_labels) - 1
    roof_bracing = bool(getattr(cfg, "roof_bracing", False))
    brace_bays = _diaphragm_brace_bays(n_bays)
    for bay_i in range(n_bays):
        bay = cfg.bay_at(bay_i)
        z0, z1 = grid.z_labels[bay_i], grid.z_labels[bay_i + 1]
        if bay_i in brace_bays:
            if bay.x_bracing_left_wall:
                members.extend(
                    _x_bracing(
                        grid, aid, grid.x_labels[0], bay_i, z0, z1, bracing_profile
                    )
                )
            if bay.x_bracing_right_wall:
                members.extend(
                    _x_bracing(
                        grid, aid, grid.x_labels[-1], bay_i, z0, z1, bracing_profile
                    )
                )
            if roof_bracing:
                members.extend(
                    _roof_bracing(
                        grid,
                        aid,
                        bay_i,
                        z0,
                        z1,
                        ridge,
                        bracing_profile,
                        truss_type=primary_truss_type,
                        use_truss=use_truss,
                    )
                )
        if bay.sag_rods:
            # Roof rods between purlins; long-wall rods between girts per Z-bay.
            members.extend(
                _roof_sag_rods(
                    grid,
                    aid,
                    bay_i,
                    z0,
                    z1,
                    purlin_spacing_mm=cfg.purlin_spacing_mm,
                    profile=sag_rod_profile,
                )
            )
            if has_wall_girts and bay.wall_girts:
                members.extend(
                    _long_wall_sag_rods(
                        grid, aid, bay_i, z0, z1, girt_levels, sag_rod_profile
                    )
                )

    any_sag_rods = any(cfg.bay_at(i).sag_rods for i in range(n_bays))
    if generate_gable and has_wall_girts and any_sag_rods:
        members.extend(
            _gable_wall_sag_rods(
                grid, aid, girt_levels, gable_post_spacing, sag_rod_profile
            )
        )

    # End-wall (gable) bracing — one corner-bay panel per end wall, between two
    # adjacent end-wall columns (aligned to the gable post lines).
    if bool(getattr(cfg, "gable_bracing", False)):
        members.extend(
            _end_wall_bracing(
                grid, aid, gable_post_spacing, bracing_profile, trussed_frames=trussed_frames
            )
        )

    # Restraint / detailing members.
    if bool(getattr(cfg, "fly_braces", False)):
        members.extend(
            _fly_braces(
                grid,
                aid,
                ridge,
                cfg.purlin_spacing_mm,
                bracing_profile,
                trussed_frames=trussed_frames,
            )
        )
    if bool(getattr(cfg, "bottom_chord_restraint", False)):
        members.extend(
            _bottom_chord_restraint(
                grid,
                aid,
                trussed_frames,
                ridge_label=ridge,
                truss_type=primary_truss_type,
            )
        )
    if bool(getattr(cfg, "base_plates", False)):
        members.extend(
            _base_plates(
                grid, aid, gable_post_spacing, generate_gable, base_plate_profile
            )
        )

    preserve_bracing = (
        roof_bracing
        or bool(getattr(cfg, "gable_bracing", False))
        or bool(getattr(cfg, "fly_braces", False))
        or any(
            cfg.bay_at(i).x_bracing_left_wall or cfg.bay_at(i).x_bracing_right_wall
            for i in range(n_bays)
        )
    )
    return _strip_truss_secondary_bracing(
        members,
        trussed_frames=trussed_frames,
        z_labels=grid.z_labels,
        preserve_bracing=preserve_bracing,
    )


def _strip_truss_secondary_bracing(
    members: list[StructuralMember],
    *,
    trussed_frames: set[str],
    z_labels: list[str],
    preserve_bracing: bool = False,
) -> list[StructuralMember]:
    """Drop fly braces and X-bracing on all-truss sheds unless explicitly requested."""
    if preserve_bracing or len(trussed_frames) < len(z_labels):
        return members
    out: list[StructuralMember] = []
    for m in members:
        if m.element_type in ("bracing", "fly_brace"):
            continue
        out.append(m)
    return out

"""
Canonical portal-frame shed builder on the universal grid.

Emits grid-referenced StructuralMembers only (no absolute mm, no per-element trig).
One builder, correct geometry: primary frame, real purlins (run along the length and
seated on the rafters), side + gable wall girts, gable posts, real trusses, X-bracing
pairs and sag-rod runs. All coordinates are resolved later by the spatial grid engine.
"""

from __future__ import annotations

from core.roof_geometry import roof_elevation_at_x
from core.spatial_grid import StructuralGridEngine
from schemas.shed_assembly_config import ShedAssemblyConfig
from schemas.spatial_grid import GridDefinition, GridNodeReference, StructuralMember

# Purlin/girt seating (outside column/rafter face, 90° to support) is applied in
# member_resolver via engineering_rules after grid nodes are resolved.
_MAX_DIV_PER_SPAN = 12


def _ref(
    x: str, z: str, elev: str, offset: dict[str, float] | None = None
) -> GridNodeReference:
    return GridNodeReference(x_axis=x, z_axis=z, elevation=elev, offset_mm=offset or {})


def _roof_elev_at(grid: StructuralGridEngine, x_mm: float) -> float:
    return roof_elevation_at_x(x_mm, grid.roof, grid.total_width_mm)


def _is_eave_line(grid: StructuralGridEngine, x_label: str) -> bool:
    x_mm = grid.x_coords_mm[x_label]
    return abs(_roof_elev_at(grid, x_mm) - grid.roof.eave_y) < 1.0


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
    """X references across the full width at ~spacing, following the roof slope."""
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


def _column_top_elev(grid: StructuralGridEngine, x_label: str) -> str:
    return "eave" if _is_eave_line(grid, x_label) else "roof"


# --------------------------------------------------------------------------- #
# Individual structural systems                                               #
# --------------------------------------------------------------------------- #


def _columns(
    grid: StructuralGridEngine,
    aid: str,
    trussed_frames: set[str],
) -> list[StructuralMember]:
    """Columns to the level where their roof structure connects.

    Rafter frame: column rises to the roof line at its X (eave on eave walls, apex at
    a ridge/interior line). Truss frame: the truss bottom chord sits at eave and spans
    the full width, so EVERY column at that frame stops at eave (the truss bears on top).
    """
    out: list[StructuralMember] = []
    for x_label in grid.x_labels:
        roofline_top = _column_top_elev(grid, x_label)
        for z_label in grid.z_labels:
            top = "eave" if z_label in trussed_frames else roofline_top
            out.append(
                StructuralMember(
                    id=f"{aid}-col-{x_label}-{z_label}",
                    element_type="column",
                    profile="HEA200",
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


def _truss_frame(
    grid: StructuralGridEngine,
    aid: str,
    z_label: str,
    truss_type: str,
    ridge_label: str | None,
) -> list[StructuralMember]:
    left, right = grid.x_labels[0], grid.x_labels[-1]
    out: list[StructuralMember] = []

    # Bottom chord (tension tie at eave level, full width).
    out.append(
        StructuralMember(
            id=f"{aid}-truss-bc-{z_label}",
            element_type="truss_chord",
            profile="IPE200",
            start_node=_ref(left, z_label, "eave"),
            end_node=_ref(right, z_label, "eave"),
        )
    )
    # Top chord follows the roof line.
    if grid.roof.is_mono or ridge_label in (None, left, right):
        lo_e = "eave" if _is_eave_line(grid, left) else "roof"
        hi_e = "eave" if _is_eave_line(grid, right) else "roof"
        out.append(
            StructuralMember(
                id=f"{aid}-truss-tc-{z_label}",
                element_type="truss_chord",
                profile="IPE200",
                start_node=_ref(left, z_label, lo_e),
                end_node=_ref(right, z_label, hi_e),
            )
        )
    else:
        out.append(
            StructuralMember(
                id=f"{aid}-truss-tcL-{z_label}",
                element_type="truss_chord",
                profile="IPE200",
                start_node=_ref(left, z_label, "eave"),
                end_node=_ref(ridge_label, z_label, "apex"),
            )
        )
        out.append(
            StructuralMember(
                id=f"{aid}-truss-tcR-{z_label}",
                element_type="truss_chord",
                profile="IPE200",
                start_node=_ref(ridge_label, z_label, "apex"),
                end_node=_ref(right, z_label, "eave"),
            )
        )

    # Web members at interior panel points (verticals + diagonals).
    span = grid.total_width_mm
    panel_xs = _roof_x_positions(grid, max(1500.0, span / 6.0))
    interior = [x for x in panel_xs if x not in (left, right)]
    prev = left
    for k, xr in enumerate(interior):
        out.append(
            StructuralMember(
                id=f"{aid}-truss-web-v-{z_label}-{k}",
                element_type="truss_web",
                profile="L50x50",
                start_node=_ref(xr, z_label, "eave"),
                end_node=_ref(xr, z_label, "roof"),
            )
        )
        if truss_type != "warren" or k % 2 == 0:
            out.append(
                StructuralMember(
                    id=f"{aid}-truss-web-d-{z_label}-{k}",
                    element_type="truss_web",
                    profile="L50x50",
                    start_node=_ref(prev, z_label, "eave"),
                    end_node=_ref(xr, z_label, "roof"),
                )
            )
        prev = xr
    return out


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


def _purlins(
    grid: StructuralGridEngine, aid: str, spacing_mm: float
) -> list[StructuralMember]:
    if spacing_mm <= 0 or len(grid.z_labels) < 2:
        return []
    z_first, z_last = grid.z_labels[0], grid.z_labels[-1]
    out: list[StructuralMember] = []
    for i, xr in enumerate(_roof_x_positions(grid, spacing_mm)):
        out.append(
            StructuralMember(
                id=f"{aid}-purlin-{i}",
                element_type="purlin",
                profile="C150",
                start_node=_ref(xr, z_first, "roof"),
                end_node=_ref(xr, z_last, "roof"),
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
) -> list[StructuralMember]:
    """Horizontal rails on BOTH long side walls at the shared global girt levels."""
    if not levels:
        return []
    z_first, z_last = grid.z_labels[0], grid.z_labels[-1]
    walls = (grid.x_labels[0], grid.x_labels[-1])
    eave_y = grid.roof.eave_y
    out: list[StructuralMember] = []
    for wall in walls:
        top_y = _roof_elev_at(grid, grid.x_coords_mm[wall])
        for li, y_abs in enumerate(levels):
            if y_abs > top_y + 1.0:
                continue
            elev, y_off = _girt_nodes_at_y(y_abs, eave_y)
            out.append(
                StructuralMember(
                    id=f"{aid}-girt-{wall}-L{li}",
                    element_type="wall_girt",
                    profile="C150",
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

    Same rule as columns: on a rafter gable they rise to the roofline (framing the
    gable triangle); on a truss gable they stop at the bottom chord (the truss frames
    the roof above), so they never poke up through the truss like interior columns.
    """
    xs = _roof_x_positions(grid, spacing_mm if spacing_mm > 0 else 3000.0)
    main = set(grid.x_labels)
    out: list[StructuralMember] = []
    for z_label in (grid.z_labels[0], grid.z_labels[-1]):
        top = "eave" if z_label in trussed_frames else "roof"
        for i, xr in enumerate(xs):
            if xr in main:
                continue  # main columns already stand on the grid lines
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
) -> list[StructuralMember]:
    """Fill END walls at the same global levels as the side walls.

    Girts are never sloped. Each level is one continuous horizontal line across all
    columns that qualify; it only shortens near the roof peak where the slope cuts in.
    """
    if not levels:
        return []
    xs = _roof_x_positions(grid, post_spacing_mm if post_spacing_mm > 0 else 3000.0)
    if len(xs) < 2:
        return []
    eave_y = grid.roof.eave_y
    roof_at = {x: _roof_elev_at(grid, grid.resolve_x_mm(x)) for x in xs}
    out: list[StructuralMember] = []
    ends = (grid.z_labels[0], grid.z_labels[-1])

    for z_label in ends:
        for li, y_abs in enumerate(levels):
            cols = [x for x in xs if roof_at[x] >= y_abs - 1.0]
            if len(cols) < 2:
                continue
            elev, y_off = _girt_nodes_at_y(y_abs, eave_y)
            out.append(
                StructuralMember(
                    id=f"{aid}-gablegirt-{z_label}-L{li}",
                    element_type="wall_girt",
                    profile="C150",
                    start_node=_ref(cols[0], z_label, elev, y_off),
                    end_node=_ref(cols[-1], z_label, elev, y_off),
                )
            )
    return out


def _x_bracing(
    grid: StructuralGridEngine, aid: str, wall: str, bay_i: int, z0: str, z1: str
) -> list[StructuralMember]:
    top = _column_top_elev(grid, wall)
    return [
        StructuralMember(
            id=f"{aid}-brace-{wall}-b{bay_i}-a",
            element_type="bracing",
            profile="L50x50",
            start_node=_ref(wall, z0, "ground"),
            end_node=_ref(wall, z1, top),
        ),
        StructuralMember(
            id=f"{aid}-brace-{wall}-b{bay_i}-b",
            element_type="bracing",
            profile="L50x50",
            start_node=_ref(wall, z0, top),
            end_node=_ref(wall, z1, "ground"),
        ),
    ]


def _sag_rods(
    grid: StructuralGridEngine,
    aid: str,
    bay_i: int,
    z0: str,
    z1: str,
    purlin_spacing_mm: float,
) -> list[StructuralMember]:
    """Anti-sag rods between EACH adjacent purlin, in 1-2 rows per bay (LTB control).

    Uses the same X lines as the purlins so the rods actually wire purlin-to-purlin.
    Wide bays (> 5.5 m) get two rows at 1/3 and 2/3; otherwise a single mid-span row.
    """
    from core.engineering_rules import sag_rod_bay_fractions

    xs = _roof_x_positions(grid, purlin_spacing_mm if purlin_spacing_mm > 0 else 1200.0)
    if len(xs) < 2:
        return []
    bay_len = grid.z_coords_mm[z1] - grid.z_coords_mm[z0]
    fracs = sag_rod_bay_fractions(bay_len)
    den = len(fracs) + 1  # 2 → "+1/2"; 3 → "+1/3","+2/3"
    rows = [f"{z0}+{i}/{den}" for i in range(1, den)]
    out: list[StructuralMember] = []
    for r, zr in enumerate(rows):
        for k, (left, right) in enumerate(zip(xs, xs[1:])):
            out.append(
                StructuralMember(
                    id=f"{aid}-sag-b{bay_i}-r{r}-{k}",
                    element_type="sag_rod",
                    profile="ROD12",
                    start_node=_ref(left, zr, "roof"),
                    end_node=_ref(right, zr, "roof"),
                )
            )
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
        generate_tie_beams=bool(getattr(grid_def, "generate_tie_beams", True)),
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

    # Determine which frames carry a truss (their columns stop at the bottom chord).
    frame_truss: list[tuple[str, bool, str]] = []
    trussed_frames: set[str] = set()
    for zi, z_label in enumerate(grid.z_labels):
        uses_truss, ttype = cfg.frame_uses_truss(zi)
        frame_truss.append((z_label, uses_truss, ttype))
        if uses_truss:
            trussed_frames.add(z_label)

    # Primary frame: columns, then rafters or trusses per frame.
    members.extend(_columns(grid, aid, trussed_frames))
    for z_label, uses_truss, ttype in frame_truss:
        if uses_truss:
            members.extend(_truss_frame(grid, aid, z_label, ttype, ridge))
        else:
            members.extend(_rafters(grid, aid, z_label, ridge))

    # Longitudinal stability: eave/ridge ties tying the frames together.
    if cfg.generate_tie_beams:
        members.extend(_eave_ridge_ties(grid, aid, ridge))

    # Roof purlins (run along the length, seated on the rafters).
    members.extend(_purlins(grid, aid, cfg.purlin_spacing_mm))

    # Gable post spacing: ~2x the girt spacing, but fine enough that each roof slope
    # gets at least one intermediate post so horizontal gable girts can step up the
    # slope and fill the gable (a straight girt to a bare ridge post can't rise).
    gable_post_spacing = min(cfg.girt_spacing_mm * 2, max(grid.total_width_mm / 4, 1.0))

    # Wall infill: one shared girt level schedule wraps all walls at the same EL.
    if any(cfg.bay_at(i).wall_girts for i in range(len(grid.z_labels) - 1)):
        girt_levels = _global_girt_levels(
            grid.roof.eave_y,
            grid.roof.ridge_y,
            cfg.girt_spacing_mm,
        )
        members.extend(_side_wall_girts(grid, aid, girt_levels))
        if generate_gable:
            members.extend(_gable_girts(grid, aid, girt_levels, gable_post_spacing))
    if generate_gable:
        members.extend(_gable_posts(grid, aid, gable_post_spacing, trussed_frames))

    # Per-bay bracing and sag rods.
    for bay_i in range(len(grid.z_labels) - 1):
        bay = cfg.bay_at(bay_i)
        z0, z1 = grid.z_labels[bay_i], grid.z_labels[bay_i + 1]
        if bay.x_bracing_left_wall:
            members.extend(_x_bracing(grid, aid, grid.x_labels[0], bay_i, z0, z1))
        if bay.x_bracing_right_wall:
            members.extend(_x_bracing(grid, aid, grid.x_labels[-1], bay_i, z0, z1))
        if bay.sag_rods:
            members.extend(
                _sag_rods(grid, aid, bay_i, z0, z1, purlin_spacing_mm=cfg.purlin_spacing_mm)
            )

    return members

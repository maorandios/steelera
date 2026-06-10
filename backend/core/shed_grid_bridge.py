"""Map parametric shed config → universal grid definition."""

from __future__ import annotations

from schemas.shed_assembly_config import ShedAssemblyConfig
from schemas.spatial_grid import GridDefinition


def grid_definition_from_shed_config(cfg: ShedAssemblyConfig) -> GridDefinition:
    """Full grid intent including catalog profiles and feature flags."""
    cfg = cfg.with_default_bays()
    gp = cfg.global_parameters
    n_bays = len(cfg.grid_layout.z_spans)
    any_truss = any(cfg.frame_uses_truss(i)[0] for i in range(n_bays + 1))
    truss_type = "none"
    for i in range(n_bays + 1):
        uses, ttype = cfg.frame_uses_truss(i)
        if uses and ttype != "none":
            truss_type = ttype
            break
    any_bracing = any(
        b.x_bracing_left_wall or b.x_bracing_right_wall for b in cfg.bays_configuration
    )
    any_sag = any(b.sag_rods for b in cfg.bays_configuration)
    any_girts = any(b.wall_girts for b in cfg.bays_configuration)

    return GridDefinition(
        x_spans=list(cfg.grid_layout.x_spans),
        z_spans=list(cfg.grid_layout.z_spans),
        height_mm=gp.height_mm,
        roof_pitch_deg=0.0 if gp.roof_style == "flat" else gp.roof_pitch_deg,
        roof_style=gp.roof_style,
        mono_high_side=getattr(cfg, "mono_high_side", "B"),
        use_truss=any_truss,
        truss_type=truss_type if any_truss else "none",
        x_bracing=any_bracing,
        gable_bracing=bool(cfg.gable_bracing),
        roof_bracing=bool(cfg.roof_bracing),
        sag_rods=any_sag,
        haunches=bool(cfg.haunches),
        fly_braces=bool(cfg.fly_braces),
        base_plates=bool(cfg.base_plates),
        bottom_chord_restraint=bool(cfg.bottom_chord_restraint),
        generate_purlins=bool(getattr(cfg, "generate_purlins", True)),
        generate_wall_girts=any_girts,
        generate_tie_beams=bool(cfg.generate_tie_beams),
        purlin_spacing_mm=float(cfg.purlin_spacing_mm),
        girt_spacing_mm=float(cfg.girt_spacing_mm),
        column_profile=cfg.column_profile,
        bracing_profile=cfg.bracing_profile,
        purlin_profile=cfg.purlin_profile,
        girt_profile=cfg.girt_profile,
        sag_rod_profile=cfg.sag_rod_profile,
        base_plate_profile=cfg.base_plate_profile,
        truss_chord_profile=cfg.truss_chord_profile,
        truss_web_profile=cfg.truss_web_profile,
        tie_beam_profile=cfg.tie_beam_profile,
    )

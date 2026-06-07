"""Convert legacy GenerateShedRequest → ShedAssemblyConfig."""

from __future__ import annotations

from core.geometry_engine import resolve_x_spans_mm, resolve_z_spans_mm
from schemas.macro import GenerateShedRequest
from schemas.shed_assembly_config import (
    ShedAssemblyConfig,
    ShedBayConfiguration,
    ShedGlobalParameters,
    ShedGridLayout,
)


def legacy_request_to_config(request: GenerateShedRequest) -> ShedAssemblyConfig:
    """Map sidebar / checklist flat API to unified parametric config."""
    x_spans = resolve_x_spans_mm(x_spans=request.x_spans, width=request.width)
    z_spans = resolve_z_spans_mm(
        z_spans=request.z_spans,
        length=request.length,
        frame_spacing=request.frame_spacing,
    )
    n_bays = len(z_spans)
    bays: list[ShedBayConfiguration] = []
    for i in range(n_bays):
        bays.append(
            ShedBayConfiguration(
                bay_index=i,
                use_truss=request.use_truss,
                truss_type=request.truss_type if request.use_truss else "none",
                x_bracing_left_wall=request.use_bracing,
                x_bracing_right_wall=request.use_bracing,
                wall_girts=request.generate_wall_girts,
                sag_rods=request.use_sag_rods,
            )
        )
    return ShedAssemblyConfig(
        assembly_id=request.assembly_id,
        replace_existing=request.replace_existing,
        global_parameters=ShedGlobalParameters(
            height_mm=request.height,
            roof_pitch_deg=0.0 if request.roof_style == "flat" else request.roof_pitch_deg,
            roof_style=request.roof_style,
        ),
        grid_layout=ShedGridLayout(x_spans=x_spans, z_spans=z_spans),
        bays_configuration=bays,
        purlin_spacing_mm=request.purlin_spacing,
        girt_spacing_mm=request.girt_spacing_mm,
        column_profile=request.column_profile,
        bracing_profile=request.bracing_profile,
        purlin_profile=request.purlin_profile,
        girt_profile=request.girt_profile,
        sag_rod_profile=request.sag_rod_profile,
        base_plate_profile=request.base_plate_profile,
        generate_tie_beams=request.generate_tie_beams,
        gable_bracing=request.use_gable_bracing,
        roof_bracing=request.use_roof_bracing,
        haunches=request.use_haunches,
        fly_braces=request.use_fly_braces,
        base_plates=request.use_base_plates,
        bottom_chord_restraint=request.use_bottom_chord_restraint,
        mono_high_side=getattr(request, "mono_high_side", "B"),
    )


def legacy_kwargs_to_config(
    *,
    assembly_id: str,
    x_spans: list[float],
    z_spans: list[float],
    height: float,
    roof_pitch_deg: float,
    roof_style: str,
    replace_existing: bool,
    **kwargs: object,
) -> ShedAssemblyConfig:
    req = GenerateShedRequest.model_validate(
        {
            "assembly_id": assembly_id,
            "x_spans": x_spans,
            "z_spans": z_spans,
            "height": height,
            "roof_pitch_deg": roof_pitch_deg,
            "roof_style": roof_style,
            "replace_existing": replace_existing,
            **kwargs,
        }
    )
    return legacy_request_to_config(req)

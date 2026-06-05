import {
  DEFAULT_SHED_PARAMS,
  formatSpansInput,
  totalFromSpans,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import type { ShedAssemblyConfig } from "@/types/shed-config";

/** Map parametric config → sidebar/store ShedAssemblyParams (inferred summaries). */
export function shedConfigToAssemblyParams(
  config: ShedAssemblyConfig,
): ShedAssemblyParams {
  const x = config.grid_layout.x_spans;
  const z = config.grid_layout.z_spans;
  const gp = config.global_parameters;
  const anyTruss = config.bays_configuration.some((b) => b.use_truss);
  const anyBracing = config.bays_configuration.some(
    (b) => b.x_bracing_left_wall || b.x_bracing_right_wall,
  );
  const anySag = config.bays_configuration.some((b) => b.sag_rods);
  const anyGirts = config.bays_configuration.some((b) => b.wall_girts);

  return {
    x_spans: x,
    z_spans: z,
    x_spans_input: formatSpansInput(x),
    z_spans_input: formatSpansInput(z),
    width: totalFromSpans(x),
    length: totalFromSpans(z),
    height: gp.height_mm,
    roof_pitch_deg: gp.roof_style === "flat" ? 0 : gp.roof_pitch_deg,
    roof_style: gp.roof_style,
    purlin_spacing: config.purlin_spacing_mm,
    girt_spacing_mm: config.girt_spacing_mm,
    use_truss: anyTruss,
    use_bracing: anyBracing,
    use_sag_rods: anySag,
    generate_wall_girts: anyGirts,
    generate_tie_beams: config.generate_tie_beams,
  };
}

export function assemblyParamsToShedConfig(
  params: ShedAssemblyParams,
  assembly_id = "shed_1",
): ShedAssemblyConfig {
  const bays = params.z_spans.map((_, bay_index) => ({
    bay_index,
    use_truss: params.use_truss,
    truss_type: params.use_truss ? ("pratt" as const) : ("none" as const),
    x_bracing_left_wall: params.use_bracing,
    x_bracing_right_wall: params.use_bracing,
    wall_girts: params.generate_wall_girts,
    sag_rods: params.use_sag_rods,
  }));

  return {
    assembly_id,
    replace_existing: true,
    global_parameters: {
      height_mm: params.height,
      roof_pitch_deg: params.roof_pitch_deg,
      roof_style: params.roof_style,
    },
    grid_layout: {
      x_spans: params.x_spans,
      z_spans: params.z_spans,
    },
    bays_configuration: bays,
    purlin_spacing_mm: params.purlin_spacing,
    girt_spacing_mm: params.girt_spacing_mm,
    generate_tie_beams: params.generate_tie_beams,
  };
}

export function defaultShedAssemblyConfig(): ShedAssemblyConfig {
  return assemblyParamsToShedConfig(DEFAULT_SHED_PARAMS);
}

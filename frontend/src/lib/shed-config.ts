import {
  DEFAULT_SHED_PARAMS,
  formatSpansInput,
  totalFromSpans,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import type { ShedAssemblyConfig, TrussType } from "@/types/shed-config";

const SELECTABLE_TRUSS_TYPES: ReadonlySet<string> = new Set([
  "pratt",
  "howe",
  "warren",
  "fink",
  "king_post",
  "queen_post",
  "scissor",
]);

/** Map parametric config → sidebar/store ShedAssemblyParams (inferred summaries). */
export function shedConfigToAssemblyParams(
  config: ShedAssemblyConfig,
): ShedAssemblyParams {
  const x = config.grid_layout.x_spans;
  const z = config.grid_layout.z_spans;
  const gp = config.global_parameters;
  const anyTruss = config.bays_configuration.some((b) => b.use_truss);
  const trussBay = config.bays_configuration.find(
    (b) => b.use_truss && SELECTABLE_TRUSS_TYPES.has(b.truss_type),
  );
  const anyBracing = config.bays_configuration.some(
    (b) => b.x_bracing_left_wall || b.x_bracing_right_wall,
  );
  const anySag = config.bays_configuration.some((b) => b.sag_rods);
  const anyGirts = config.bays_configuration.some((b) => b.wall_girts);

  return {
    use_gable_bracing: Boolean(config.gable_bracing),
    use_roof_bracing: Boolean(config.roof_bracing),
    use_haunches: Boolean(config.haunches),
    use_fly_braces: Boolean(config.fly_braces),
    use_base_plates: Boolean(config.base_plates),
    use_bottom_chord_restraint: Boolean(config.bottom_chord_restraint),
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
    truss_type: (trussBay?.truss_type ?? "pratt") as Exclude<TrussType, "none">,
    use_bracing: anyBracing,
    use_sag_rods: anySag,
    generate_wall_girts: anyGirts,
    generate_tie_beams: config.generate_tie_beams,
    column_profile: config.column_profile ?? null,
    bracing_profile: config.bracing_profile ?? null,
    purlin_profile: config.purlin_profile ?? null,
    girt_profile: config.girt_profile ?? null,
    sag_rod_profile: config.sag_rod_profile ?? null,
    base_plate_profile: config.base_plate_profile ?? null,
  };
}

export function assemblyParamsToShedConfig(
  params: ShedAssemblyParams,
  assembly_id = "shed_1",
): ShedAssemblyConfig {
  const bays = params.z_spans.map((_, bay_index) => ({
    bay_index,
    use_truss: params.use_truss,
    truss_type: params.use_truss ? params.truss_type : ("none" as const),
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
    column_profile: params.column_profile ?? null,
    bracing_profile: params.bracing_profile ?? null,
    purlin_profile: params.purlin_profile ?? null,
    girt_profile: params.girt_profile ?? null,
    sag_rod_profile: params.sag_rod_profile ?? null,
    base_plate_profile: params.base_plate_profile ?? null,
    generate_tie_beams: params.generate_tie_beams,
    gable_bracing: params.use_gable_bracing,
    roof_bracing: params.use_roof_bracing,
    haunches: params.use_haunches,
    fly_braces: params.use_fly_braces,
    base_plates: params.use_base_plates,
    bottom_chord_restraint: params.use_bottom_chord_restraint,
  };
}

export function defaultShedAssemblyConfig(): ShedAssemblyConfig {
  return assemblyParamsToShedConfig(DEFAULT_SHED_PARAMS);
}

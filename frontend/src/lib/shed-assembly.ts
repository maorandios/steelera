import type { GenerateShedParams, ShedRoofStyle } from "@/types/macro";
import type { ProjectElementMm } from "@/types/project";
import type { TrussType } from "@/types/shed-config";

export type { ShedRoofStyle };

export const SHED_ASSEMBLY_ID = "shed_1";
export const SHED_ASSEMBLY_LABEL = "Portal Frame Shed";

export interface ShedAssemblyParams {
  x_spans: number[];
  z_spans: number[];
  x_spans_input: string;
  z_spans_input: string;
  width: number;
  length: number;
  height: number;
  roof_pitch_deg: number;
  roof_style: ShedRoofStyle;
  purlin_spacing: number;
  girt_spacing_mm: number;
  use_truss: boolean;
  truss_type: Exclude<TrussType, "none">;
  use_bracing: boolean;
  use_gable_bracing: boolean;
  use_roof_bracing: boolean;
  use_sag_rods: boolean;
  use_haunches: boolean;
  use_fly_braces: boolean;
  use_base_plates: boolean;
  use_bottom_chord_restraint: boolean;
  generate_wall_girts: boolean;
  generate_tie_beams: boolean;
}

export const DEFAULT_SHED_PARAMS: ShedAssemblyParams = {
  x_spans: [3000, 7000, 10000, 5000],
  z_spans: [5000, 5000, 5000, 5000, 5000, 5000],
  x_spans_input: "3000, 7000, 10000, 5000",
  z_spans_input: "5000, 5000, 5000, 5000, 5000, 5000",
  width: 25000,
  length: 30000,
  height: 4000,
  roof_pitch_deg: 10,
  roof_style: "duo_pitch",
  purlin_spacing: 1200,
  girt_spacing_mm: 1500,
  use_truss: false,
  truss_type: "pratt",
  use_bracing: false,
  use_gable_bracing: false,
  use_roof_bracing: false,
  use_sag_rods: false,
  use_haunches: false,
  use_fly_braces: false,
  use_base_plates: false,
  use_bottom_chord_restraint: false,
  generate_wall_girts: true,
  generate_tie_beams: true,
};

/** Parse "3000, 7000" → bay widths [3000, 7000] (mm). */
export function parseBaySpansMm(input: string): number[] | null {
  const tokens = input
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (tokens.length === 0) {
    return null;
  }

  const spans: number[] = [];
  for (const token of tokens) {
    const step = Number(token);
    if (!Number.isFinite(step) || step <= 0) {
      return null;
    }
    spans.push(Math.round(step * 1000) / 1000);
  }

  return spans;
}

export function formatSpansInput(spans: number[]): string {
  return spans.map((value) => String(Math.round(value))).join(", ");
}

export function totalFromSpans(spans: number[]): number {
  return spans.reduce((sum, step) => sum + step, 0);
}

export function isShedAssemblyMember(
  element: ProjectElementMm | null | undefined,
): boolean {
  return element?.assembly_id === SHED_ASSEMBLY_ID;
}

function inferSpansFromAxis(
  values: number[],
  fallback: number[],
): number[] {
  const sorted = [...new Set(values.map((v) => Math.round(v * 1000) / 1000))].sort(
    (a, b) => a - b,
  );
  if (sorted.length >= 2) {
    const spans: number[] = [];
    for (let i = 1; i < sorted.length; i += 1) {
      spans.push(Math.round((sorted[i] - sorted[i - 1]) * 1000) / 1000);
    }
    return spans;
  }
  if (sorted.length === 1 && sorted[0] > 0) {
    return [sorted[0]];
  }
  return fallback;
}

function memberHasType(
  members: ProjectElementMm[],
  elementType: string,
): boolean {
  return members.some(
    (m) =>
      m.element_type === elementType ||
      m.id.includes(elementType.replace("_", "-")),
  );
}

export function inferShedParamsFromElements(
  elements: ProjectElementMm[],
): ShedAssemblyParams | null {
  const members = elements.filter((e) => e.assembly_id === SHED_ASSEMBLY_ID);
  if (members.length === 0) return null;

  const cols = members.filter((e) => e.id.startsWith("shed-col"));
  const leftRafters = members.filter((e) => e.id.startsWith("shed-raf-L"));
  const monoRafters = members.filter((e) => e.id.startsWith("shed-raf-") && !e.id.includes("L") && !e.id.includes("R"));
  const flatRafters = members.filter(
    (e) => e.id.startsWith("shed-raf-") && !e.id.includes("L") && !e.id.includes("R"),
  );

  const x_spans = inferSpansFromAxis(
    cols.map((c) => c.position_mm.x),
    DEFAULT_SHED_PARAMS.x_spans,
  );
  const z_spans = inferSpansFromAxis(
    cols.map((c) => c.position_mm.z),
    DEFAULT_SHED_PARAMS.z_spans,
  );

  let roof_pitch_deg = DEFAULT_SHED_PARAMS.roof_pitch_deg;
  const euler = leftRafters[0]?.rotation_euler_deg ?? monoRafters[0]?.rotation_euler_deg;
  if (euler && euler.length >= 3) {
    roof_pitch_deg = Math.abs(euler[2]);
  }

  let roof_style: ShedRoofStyle = "duo_pitch";
  if (memberHasType(members, "truss_chord") || members.some((m) => m.id.includes("shed-truss"))) {
    // truss mode — roof style from geometry
  }
  if (leftRafters.length === 0) {
    const singleRafter = flatRafters.find((r) => r.rotation_euler_deg?.every((v) => v === 0));
    if (singleRafter) {
      roof_style = "flat";
      roof_pitch_deg = 0;
    } else if (monoRafters.length > 0) {
      roof_style = "mono_pitch";
    }
  }

  return {
    ...DEFAULT_SHED_PARAMS,
    x_spans,
    z_spans,
    x_spans_input: formatSpansInput(x_spans),
    z_spans_input: formatSpansInput(z_spans),
    width: totalFromSpans(x_spans),
    length: totalFromSpans(z_spans),
    height:
      cols.length > 0
        ? Math.min(...cols.map((c) => c.length_mm))
        : DEFAULT_SHED_PARAMS.height,
    roof_pitch_deg,
    roof_style,
    use_truss:
      memberHasType(members, "truss_chord") ||
      members.some((m) => m.id.startsWith("shed-truss")),
    use_bracing:
      memberHasType(members, "bracing") ||
      members.some((m) => m.id.startsWith("shed-brace")),
    use_gable_bracing: members.some((m) => m.id.includes("-brace-end-")),
    use_roof_bracing: members.some((m) => m.id.includes("-brace-roof-")),
    use_sag_rods:
      memberHasType(members, "sag_rod") ||
      members.some((m) => m.id.startsWith("shed-sag")),
    generate_wall_girts:
      memberHasType(members, "wall_girt") ||
      members.some((m) => m.id.startsWith("shed-girt")),
    generate_tie_beams:
      memberHasType(members, "tie_beam") ||
      members.some((m) => m.id.startsWith("shed-tie")),
  };
}

export function mergeShedParams(
  current: ShedAssemblyParams,
  partial: Partial<ShedAssemblyParams>,
): ShedAssemblyParams {
  const x_spans = partial.x_spans ?? current.x_spans;
  const z_spans = partial.z_spans ?? current.z_spans;
  return {
    x_spans,
    z_spans,
    x_spans_input: partial.x_spans_input ?? formatSpansInput(x_spans),
    z_spans_input: partial.z_spans_input ?? formatSpansInput(z_spans),
    width: partial.width ?? totalFromSpans(x_spans),
    length: partial.length ?? totalFromSpans(z_spans),
    height: partial.height ?? current.height,
    roof_pitch_deg: partial.roof_pitch_deg ?? current.roof_pitch_deg,
    roof_style: partial.roof_style ?? current.roof_style,
    purlin_spacing: partial.purlin_spacing ?? current.purlin_spacing,
    girt_spacing_mm: partial.girt_spacing_mm ?? current.girt_spacing_mm,
    use_truss: partial.use_truss ?? current.use_truss,
    truss_type: partial.truss_type ?? current.truss_type,
    use_bracing: partial.use_bracing ?? current.use_bracing,
    use_gable_bracing: partial.use_gable_bracing ?? current.use_gable_bracing,
    use_roof_bracing: partial.use_roof_bracing ?? current.use_roof_bracing,
    use_sag_rods: partial.use_sag_rods ?? current.use_sag_rods,
    use_haunches: partial.use_haunches ?? current.use_haunches,
    use_fly_braces: partial.use_fly_braces ?? current.use_fly_braces,
    use_base_plates: partial.use_base_plates ?? current.use_base_plates,
    use_bottom_chord_restraint:
      partial.use_bottom_chord_restraint ?? current.use_bottom_chord_restraint,
    generate_wall_girts:
      partial.generate_wall_girts ?? current.generate_wall_girts,
    generate_tie_beams:
      partial.generate_tie_beams ?? current.generate_tie_beams,
  };
}

export type ShedFormValues = {
  xSpans: string;
  zSpans: string;
  height: string;
  pitch: string;
  purlinSpacing: string;
  girtSpacing: string;
  roofStyle: ShedRoofStyle;
  useTruss: boolean;
  useBracing: boolean;
  useSagRods: boolean;
  generateWallGirts: boolean;
};

export function shedParamsToFormStrings(params: ShedAssemblyParams): ShedFormValues {
  return {
    xSpans: params.x_spans_input,
    zSpans: params.z_spans_input,
    height: String(Math.round(params.height)),
    pitch: String(params.roof_pitch_deg),
    purlinSpacing: String(Math.round(params.purlin_spacing)),
    girtSpacing: String(Math.round(params.girt_spacing_mm)),
    roofStyle: params.roof_style,
    useTruss: params.use_truss,
    useBracing: params.use_bracing,
    useSagRods: params.use_sag_rods,
    generateWallGirts: params.generate_wall_girts,
  };
}

export function parseShedFormValues(
  form: ShedFormValues,
): { params: ShedAssemblyParams } | { error: string } {
  const parsePositive = (value: string) => {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  const x_spans = parseBaySpansMm(form.xSpans);
  const z_spans = parseBaySpansMm(form.zSpans);
  const h = parsePositive(form.height);
  const purlin = parsePositive(form.purlinSpacing);
  const girt = parsePositive(form.girtSpacing);
  const p = Number(form.pitch);

  if (x_spans == null) {
    return {
      error:
        'X spans must be comma-separated positive numbers (mm), e.g. "3000, 7000, 10000, 5000".',
    };
  }
  if (z_spans == null) {
    return {
      error:
        'Z spans must be comma-separated positive numbers (mm), e.g. "5000, 5000, 5000".',
    };
  }
  if (h == null) {
    return { error: "Height must be a positive number (mm)." };
  }
  if (purlin == null) {
    return { error: "Purlin spacing must be a positive number (mm)." };
  }
  if (girt == null) {
    return { error: "Girt spacing must be a positive number (mm)." };
  }
  if (form.roofStyle !== "flat" && (!Number.isFinite(p) || p < 0 || p >= 90)) {
    return { error: "Roof pitch must be between 0° and 90°." };
  }

  const roof_pitch_deg = form.roofStyle === "flat" ? 0 : p;

  return {
    params: {
      x_spans,
      z_spans,
      x_spans_input: formatSpansInput(x_spans),
      z_spans_input: formatSpansInput(z_spans),
      width: totalFromSpans(x_spans),
      length: totalFromSpans(z_spans),
      height: h,
      roof_pitch_deg,
      roof_style: form.roofStyle,
      purlin_spacing: purlin,
      girt_spacing_mm: girt,
      use_truss: form.useTruss,
      truss_type: DEFAULT_SHED_PARAMS.truss_type,
      use_bracing: form.useBracing,
      use_gable_bracing: DEFAULT_SHED_PARAMS.use_gable_bracing,
      use_roof_bracing: DEFAULT_SHED_PARAMS.use_roof_bracing,
      use_sag_rods: form.useSagRods,
      use_haunches: DEFAULT_SHED_PARAMS.use_haunches,
      use_fly_braces: DEFAULT_SHED_PARAMS.use_fly_braces,
      use_base_plates: DEFAULT_SHED_PARAMS.use_base_plates,
      use_bottom_chord_restraint: DEFAULT_SHED_PARAMS.use_bottom_chord_restraint,
      generate_wall_girts: form.generateWallGirts,
      generate_tie_beams: DEFAULT_SHED_PARAMS.generate_tie_beams,
    },
  };
}

export function shedParamsToApiPayload(
  params: ShedAssemblyParams,
): Omit<GenerateShedParams, "assembly_id" | "replace_existing"> {
  const pitch =
    params.roof_style === "flat" ? 0 : params.roof_pitch_deg;
  return {
    x_spans: params.x_spans,
    z_spans: params.z_spans,
    height: params.height,
    roof_pitch_deg: pitch,
    roof_style: params.roof_style,
    purlin_spacing: params.purlin_spacing,
    girt_spacing_mm: params.girt_spacing_mm,
    use_truss: params.use_truss,
    truss_type: params.truss_type,
    use_bracing: params.use_bracing,
    use_gable_bracing: params.use_gable_bracing,
    use_roof_bracing: params.use_roof_bracing,
    use_sag_rods: params.use_sag_rods,
    use_haunches: params.use_haunches,
    use_fly_braces: params.use_fly_braces,
    use_base_plates: params.use_base_plates,
    use_bottom_chord_restraint: params.use_bottom_chord_restraint,
    generate_wall_girts: params.generate_wall_girts,
    generate_tie_beams: params.generate_tie_beams,
  };
}

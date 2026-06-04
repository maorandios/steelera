import type { ProjectElementMm } from "@/types/project";

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
  purlin_spacing?: number;
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
  purlin_spacing: 1200,
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

export function inferShedParamsFromElements(
  elements: ProjectElementMm[],
): ShedAssemblyParams | null {
  const members = elements.filter((e) => e.assembly_id === SHED_ASSEMBLY_ID);
  if (members.length === 0) return null;

  const cols = members.filter((e) => e.id.startsWith("shed-col"));
  const leftRafters = members.filter((e) => e.id.startsWith("shed-raf-L"));

  const x_spans = inferSpansFromAxis(
    cols.map((c) => c.position_mm.x),
    DEFAULT_SHED_PARAMS.x_spans,
  );
  const z_spans = inferSpansFromAxis(
    cols.map((c) => c.position_mm.z),
    DEFAULT_SHED_PARAMS.z_spans,
  );

  let roof_pitch_deg = DEFAULT_SHED_PARAMS.roof_pitch_deg;
  const euler = leftRafters[0]?.rotation_euler_deg;
  if (euler && euler.length >= 3) {
    roof_pitch_deg = euler[2];
  }

  return {
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
    purlin_spacing: DEFAULT_SHED_PARAMS.purlin_spacing,
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
    purlin_spacing: partial.purlin_spacing ?? current.purlin_spacing,
  };
}

export function shedParamsToFormStrings(params: ShedAssemblyParams) {
  return {
    xSpans: params.x_spans_input,
    zSpans: params.z_spans_input,
    height: String(Math.round(params.height)),
    pitch: String(params.roof_pitch_deg),
    purlinSpacing: String(
      Math.round(params.purlin_spacing ?? DEFAULT_SHED_PARAMS.purlin_spacing!),
    ),
  };
}

export function parseShedFormValues(
  xSpans: string,
  zSpans: string,
  height: string,
  pitch: string,
  purlinSpacing: string,
): { params: ShedAssemblyParams } | { error: string } {
  const parsePositive = (value: string) => {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  const x_spans = parseBaySpansMm(xSpans);
  const z_spans = parseBaySpansMm(zSpans);
  const h = parsePositive(height);
  const purlin = parsePositive(purlinSpacing);
  const p = Number(pitch);

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
  if (!Number.isFinite(p) || p < 0 || p >= 90) {
    return { error: "Roof pitch must be between 0° and 90°." };
  }

  return {
    params: {
      x_spans,
      z_spans,
      x_spans_input: formatSpansInput(x_spans),
      z_spans_input: formatSpansInput(z_spans),
      width: totalFromSpans(x_spans),
      length: totalFromSpans(z_spans),
      height: h,
      roof_pitch_deg: p,
      purlin_spacing: purlin,
    },
  };
}

export function shedParamsToApiPayload(params: ShedAssemblyParams) {
  return {
    x_spans: params.x_spans,
    z_spans: params.z_spans,
    height: params.height,
    roof_pitch_deg: params.roof_pitch_deg,
    purlin_spacing: params.purlin_spacing ?? DEFAULT_SHED_PARAMS.purlin_spacing!,
  };
}

import {
  DEFAULT_SHED_PARAMS,
  formatSpansInput,
  parseBaySpansMm,
  totalFromSpans,
  type ShedAssemblyParams,
} from "@/lib/shed-assembly";
import type { ShedChecklistPayload, ShedChecklistSelections } from "@/types/chat";
import type { ShedRoofStyle } from "@/types/macro";

const DEFAULT_BAY_MM = 5000;

/** Build Z frame bays that sum to length when user did not specify z_spans. */
export function defaultZSpansForLength(lengthMm: number): number[] {
  const bays = Math.max(1, Math.round(lengthMm / DEFAULT_BAY_MM));
  return Array.from({ length: bays }, () => DEFAULT_BAY_MM);
}

export function normalizeRoofStyle(value: string | null | undefined): ShedRoofStyle {
  const key = (value ?? "duo_pitch").trim().toLowerCase().replace(/-/g, "_");
  if (key === "mono_pitch" || key === "flat" || key === "duo_pitch") {
    return key;
  }
  return "duo_pitch";
}

export function checklistPayloadToShedParams(
  payload: ShedChecklistPayload,
  selections: ShedChecklistSelections,
): ShedAssemblyParams {
  const width = payload.width_mm ?? DEFAULT_SHED_PARAMS.width;
  const length = payload.length_mm ?? DEFAULT_SHED_PARAMS.length;
  const height = payload.height_mm ?? DEFAULT_SHED_PARAMS.height;
  const roof_style = normalizeRoofStyle(payload.roof_style);
  const roof_pitch_deg =
    roof_style === "flat"
      ? 0
      : (payload.roof_pitch_deg ?? DEFAULT_SHED_PARAMS.roof_pitch_deg);

  const x_spans =
    parseBaySpansMm(payload.x_spans?.trim() || String(Math.round(width))) ?? [
      Math.round(width),
    ];
  const z_spans =
    parseBaySpansMm(payload.z_spans?.trim() || "") ??
    defaultZSpansForLength(length);

  return {
    x_spans,
    z_spans,
    x_spans_input: payload.x_spans?.trim() || formatSpansInput(x_spans),
    z_spans_input: payload.z_spans?.trim() || formatSpansInput(z_spans),
    width: totalFromSpans(x_spans),
    length: totalFromSpans(z_spans),
    height,
    roof_pitch_deg,
    roof_style,
    purlin_spacing: DEFAULT_SHED_PARAMS.purlin_spacing,
    girt_spacing_mm: DEFAULT_SHED_PARAMS.girt_spacing_mm,
    use_truss: selections.use_truss,
    truss_type: selections.truss_type,
    use_bracing: selections.use_bracing,
    use_gable_bracing: selections.use_gable_bracing,
    use_roof_bracing: selections.use_roof_bracing,
    use_sag_rods: selections.use_sag_rods,
    use_haunches: selections.use_haunches,
    use_fly_braces: selections.use_fly_braces,
    use_base_plates: selections.use_base_plates,
    use_bottom_chord_restraint: selections.use_bottom_chord_restraint,
    generate_wall_girts: selections.generate_wall_girts,
    generate_tie_beams: selections.generate_tie_beams,
  };
}

export function formatChecklistDimensions(payload: ShedChecklistPayload): string {
  const w = payload.width_mm;
  const l = payload.length_mm;
  const h = payload.height_mm ?? DEFAULT_SHED_PARAMS.height;
  const style = normalizeRoofStyle(payload.roof_style);
  const pitch = payload.roof_pitch_deg ?? DEFAULT_SHED_PARAMS.roof_pitch_deg;

  const widthStr = w != null ? `${(w / 1000).toFixed(1)} m` : "default width";
  const lengthStr = l != null ? `${(l / 1000).toFixed(1)} m` : "default depth";
  const styleLabel =
    style === "duo_pitch"
      ? "Duo-pitch"
      : style === "mono_pitch"
        ? "Mono-pitch"
        : "Flat";

  return `${widthStr} × ${lengthStr} · ${styleLabel} · ${Math.round(h)} mm eave${
    style !== "flat" ? ` · ${pitch}° pitch` : ""
  }`;
}

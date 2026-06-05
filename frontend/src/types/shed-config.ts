import type { ShedRoofStyle } from "@/types/macro";

export type TrussType =
  | "pratt"
  | "howe"
  | "warren"
  | "fink"
  | "king_post"
  | "queen_post"
  | "scissor"
  | "none";

/** Selectable truss patterns (excludes "none") with friendly labels. */
export const TRUSS_TYPE_OPTIONS: { value: Exclude<TrussType, "none">; label: string }[] = [
  { value: "pratt", label: "Pratt" },
  { value: "howe", label: "Howe" },
  { value: "warren", label: "Warren" },
  { value: "fink", label: "Fink (W)" },
  { value: "king_post", label: "King Post" },
  { value: "queen_post", label: "Queen Post" },
  { value: "scissor", label: "Scissor" },
];

export interface ShedGlobalParameters {
  height_mm: number;
  roof_pitch_deg: number;
  roof_style: ShedRoofStyle | "flat";
}

export interface ShedGridLayout {
  x_spans: number[];
  z_spans: number[];
}

export interface ShedBayConfiguration {
  bay_index: number;
  use_truss: boolean;
  truss_type: TrussType;
  x_bracing_left_wall: boolean;
  x_bracing_right_wall: boolean;
  wall_girts: boolean;
  sag_rods: boolean;
}

export interface ShedAssemblyConfig {
  assembly_id: string;
  replace_existing: boolean;
  global_parameters: ShedGlobalParameters;
  grid_layout: ShedGridLayout;
  bays_configuration: ShedBayConfiguration[];
  purlin_spacing_mm: number;
  girt_spacing_mm: number;
  generate_tie_beams: boolean;
  gable_bracing?: boolean;
  roof_bracing?: boolean;
  haunches?: boolean;
  fly_braces?: boolean;
  base_plates?: boolean;
  bottom_chord_restraint?: boolean;
}

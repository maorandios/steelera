import type { ShedRoofStyle } from "@/types/macro";

export type GridElevation =
  | "ground"
  | "eave"
  | "roof"
  | "apex"
  | "ridge"
  | string;

export interface GridNodeReference {
  x_axis: string;
  z_axis: string;
  elevation: GridElevation;
  offset_mm?: { x?: number; y?: number; z?: number };
}

export type StructuralElementType =
  | "column"
  | "rafter"
  | "truss_chord"
  | "truss_web"
  | "purlin"
  | "wall_girt"
  | "tie_beam"
  | "bracing"
  | "x_brace"
  | "sag_rod"
  | "haunch"
  | "fly_brace"
  | "base_plate";

export interface GridDefinition {
  x_spans: number[];
  z_spans: number[];
  height_mm: number;
  roof_pitch_deg: number;
  roof_style: ShedRoofStyle | "flat";
  mono_high_side?: "A" | "B";
  use_truss?: boolean;
  truss_type?: string;
  haunches?: boolean;
  fly_braces?: boolean;
  base_plates?: boolean;
  bottom_chord_restraint?: boolean;
  x_bracing?: boolean;
  gable_bracing?: boolean;
  roof_bracing?: boolean;
  sag_rods?: boolean;
  generate_purlins?: boolean;
  generate_wall_girts?: boolean;
  generate_tie_beams?: boolean;
  purlin_spacing_mm?: number;
  girt_spacing_mm?: number;
  column_profile?: string | null;
  bracing_profile?: string | null;
  purlin_profile?: string | null;
  girt_profile?: string | null;
  sag_rod_profile?: string | null;
  base_plate_profile?: string | null;
  truss_chord_profile?: string | null;
  truss_web_profile?: string | null;
  tie_beam_profile?: string | null;
}

export interface StructuralMember {
  id: string;
  element_type: StructuralElementType;
  profile: string;
  start_node: GridNodeReference;
  end_node: GridNodeReference;
  alignment?: "center" | "start" | "end";
}

export interface StructuralGridLayout {
  assembly_id: string;
  replace_existing: boolean;
  grid_definition: GridDefinition;
  structural_members: StructuralMember[];
}

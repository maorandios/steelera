import type { ProjectElementMm, ProjectState } from "@/types/project";

export type ShedRoofStyle = "duo_pitch" | "mono_pitch" | "flat";

export interface GenerateShedParams {
  assembly_id: string;
  x_spans: number[];
  z_spans: number[];
  height: number;
  roof_pitch_deg: number;
  roof_style: ShedRoofStyle;
  purlin_spacing: number;
  girt_spacing_mm: number;
  use_truss: boolean;
  use_bracing: boolean;
  use_sag_rods: boolean;
  generate_wall_girts: boolean;
  generate_tie_beams: boolean;
  replace_existing?: boolean;
}

export interface GenerateShedResponse {
  assembly_id: string;
  elements: Record<string, unknown>[];
  projectElements: ProjectElementMm[];
  projectState: ProjectState;
  counts: {
    columns: number;
    rafters: number;
    purlins: number;
    wall_girts?: number;
    tie_beams?: number;
    bracing?: number;
    truss_chords?: number;
    truss_webs?: number;
    sag_rods?: number;
    total_generated: number;
    total_in_session: number;
  };
}

import type { StructuralTopology } from "@/types/ifc-topology";
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
  truss_type?: string;
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
  structural_topology?: StructuralTopology | null;
}

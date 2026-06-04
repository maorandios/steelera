import type { ProjectElementMm, ProjectState } from "@/types/project";

export interface GenerateShedParams {
  assembly_id: string;
  x_spans: number[];
  z_spans: number[];
  height: number;
  roof_pitch_deg: number;
  purlin_spacing?: number;
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
    total_generated: number;
    total_in_session: number;
  };
}

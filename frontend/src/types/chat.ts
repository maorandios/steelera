import type { ProjectElementMm, ProjectState } from "@/types/project";
import type { ShedRoofStyle } from "@/types/macro";

export type ChatRole = "user" | "assistant";

export type ShedChecklistPayload = {
  width_mm: number | null;
  length_mm: number | null;
  height_mm: number | null;
  roof_style: ShedRoofStyle | null;
  roof_pitch_deg: number | null;
  x_spans: string | null;
  z_spans: string | null;
};

export type ShedChecklistSelections = {
  use_bracing: boolean;
  generate_wall_girts: boolean;
  generate_tie_beams: boolean;
  use_sag_rods: boolean;
  use_truss: boolean;
};

export type ChatUiBlock = {
  type: "show_component_checklist";
  payload: ShedChecklistPayload;
};

export interface ChatMessage {
  role: ChatRole;
  content: string;
  ui_block?: ChatUiBlock | null;
}

export interface ChatResponseMessage {
  role: "assistant";
  content: string;
  ui_block?: ChatUiBlock | null;
}

export interface ChatResponse {
  message: ChatResponseMessage;
  statuses: string[];
  projectElements: ProjectElementMm[];
  projectState?: ProjectState;
}

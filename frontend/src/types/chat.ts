import type { ProjectElementMm, ProjectState } from "@/types/project";
import type { ShedRoofStyle } from "@/types/macro";
import type { TrussType } from "@/types/shed-config";
import type { StructuralGridLayout } from "@/types/spatial-grid";

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
  use_gable_bracing: boolean;
  use_roof_bracing: boolean;
  generate_wall_girts: boolean;
  generate_tie_beams: boolean;
  use_sag_rods: boolean;
  use_haunches: boolean;
  use_fly_braces: boolean;
  use_base_plates: boolean;
  use_bottom_chord_restraint: boolean;
  use_truss: boolean;
  truss_type: Exclude<TrussType, "none">;
};

export type QuickReplyOption = {
  label: string;
  value: string;
};

export type QuickRepliesPayload = {
  onboardingPhase: string;
  options: QuickReplyOption[];
  allowCustom?: boolean;
  customPlaceholder?: string;
  customUnit?: string;
};

export type WorkspaceQuickRepliesPayload = {
  question?: string;
  options: QuickReplyOption[];
  allowCustom?: boolean;
  customPlaceholder?: string;
};

export type ViewportNodePickPayload = {
  intent: "single_brace" | "full_x";
  needed: 2 | 4;
  profile?: string | null;
  instruction?: string;
};

export type ViewportGridPickPayload = {
  instruction?: string;
};

export type ChatUiBlock =
  | {
      type: "show_component_checklist";
      payload: ShedChecklistPayload;
    }
  | {
      type: "quick_replies";
      payload: QuickRepliesPayload;
    }
  | {
      type: "workspace_quick_replies";
      payload: WorkspaceQuickRepliesPayload;
    }
  | {
      type: "viewport_node_pick";
      payload: ViewportNodePickPayload;
    }
  | {
      type: "viewport_grid_pick";
      payload: ViewportGridPickPayload;
    }
  | {
      type: "location_picker";
      payload: Record<string, never>;
    }
  | {
      type: "site_refine";
      payload: Record<string, never>;
    }
  | {
      type: "map_pin_picker";
      payload: { latitude: number; longitude: number };
    }
  | {
      type: "show_proposal";
      payload: Record<string, never>;
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
  /** Universal grid layout from AI; client POSTs /api/macro/generate-shed */
  structural_grid_layout?: StructuralGridLayout | Record<string, unknown> | null;
  /** @deprecated use structural_grid_layout */
  shed_assembly_config?: Record<string, unknown> | null;
}

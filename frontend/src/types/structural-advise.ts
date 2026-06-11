export type StructuralOperationKind =
  | "place_single_member"
  | "place_x_brace"
  | "place_multi_panel_x"
  | "place_member_array"
  | "change_profile"
  | "change_truss_type"
  | "switch_to_truss"
  | "switch_to_rafter";

export type BracingPlane = "roof" | "wall_long" | "gable" | "unknown";

export type OperationProposal = {
  id: string;
  kind: StructuralOperationKind;
  label: string;
  description: string;
  recommended: boolean;
  element_kind: string;
  scope_suggestion: import("@/types/sketch").SketchApplyScope;
  warnings: string[];
  bracing_plane?: BracingPlane | null;
  panel_count?: number | null;
  leg_start_mm?: { x: number; y: number; z: number } | null;
  leg_end_mm?: { x: number; y: number; z: number } | null;
  x_corners_mm?: { x: number; y: number; z: number }[] | null;
  profile_suggestions?: import("@/types/sketch").SketchProfileOption[];
};

export type StructuralAdviseResult = {
  summary: string;
  intent: import("@/types/sketch").StructuralIntentResult | null;
  operations: OperationProposal[];
  recommended_operation_id: string | null;
  profiles: import("@/types/sketch").SketchProfileOption[];
  scope_suggestion: import("@/types/sketch").SketchApplyScope;
  scope_reason: string;
  alternatives: import("@/types/sketch").StructuralIntentKind[];
  ai_available: boolean;
};

export type SnapNodeTier = "primary" | "secondary";

export type EnrichedSnapNode = {
  id: string;
  x: number;
  y: number;
  z: number;
  tier: SnapNodeTier;
  elementId: string;
  elementType: string;
  /** 0 = start, 1 = end, or fractional position along member */
  paramAlongMember: number;
};

export type SketchDrawPhase = "idle" | "picking" | "dialogue";

export type StructuralIntentKind =
  | "tie_beam"
  | "bracing"
  | "purlin"
  | "beam"
  | "unknown";

export type SketchApplyScope = "all_bays" | "row" | "single";

export type StructuralIntentResult = {
  kind: StructuralIntentKind;
  confidence: number;
  label: string;
  angleClass: "horizontal" | "vertical" | "diagonal";
  spanMm: number;
  start: { elementType: string; z: number; elementId: string };
  end: { elementType: string; z: number; elementId: string };
};

export type SketchLockedLine = {
  start: EnrichedSnapNode;
  end: EnrichedSnapNode;
};

export type SketchProfileTier = "light" | "recommended" | "conservative";

export type SketchProfileOption = {
  profile: string;
  tier: SketchProfileTier;
  tier_label: string;
  utilization: number;
  governing: string;
};

export type SketchAnalysisResult = {
  intent: StructuralIntentResult;
  profiles: SketchProfileOption[];
  message: string;
  scope_suggestion: SketchApplyScope;
  scope_reason: string;
  alternatives: StructuralIntentKind[];
  ai_available: boolean;
  operations?: import("@/types/structural-advise").OperationProposal[];
  recommended_operation_id?: string | null;
  summary?: string;
};

export type SketchSession = {
  phase: SketchDrawPhase;
  firstNodeId: string | null;
  lockedLine: SketchLockedLine | null;
  intent: StructuralIntentResult | null;
  intentOverride: StructuralIntentKind | null;
  analysis: SketchAnalysisResult | null;
  analysisLoading: boolean;
  selectedOperationId: string | null;
  dialogueStep: 1 | 2 | 3;
  selectedProfile: string | null;
  applyScope: SketchApplyScope | null;
};

export const SKETCH_INTENT_OPTIONS: { kind: StructuralIntentKind; label: string }[] =
  [
    { kind: "tie_beam", label: "Tie Beam" },
    { kind: "bracing", label: "Bracing" },
    { kind: "purlin", label: "Purlin" },
    { kind: "beam", label: "Beam" },
  ];

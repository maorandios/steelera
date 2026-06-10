export type ViewportMode = "inspect" | "pick_nodes" | "pick_grid";

export type PlacementIntent = "single_brace" | "full_x" | "insert_frame";

export type SnapNode = {
  id: string;
  x: number;
  y: number;
  z: number;
};

export type PickedNode = {
  snapId: string;
  x: number;
  y: number;
  z: number;
};

export type BracingPlane = "roof" | "wall_long" | "gable" | "custom" | "unknown";

export type ParentAssembly =
  | "frame"
  | "truss"
  | "bracing"
  | "purlin_run"
  | "girt_run"
  | "member";

export type ProfileScope =
  | "selection"
  | "pair"
  | "group"
  | "frame"
  | "truss"
  | "element_type";

export type SelectionContext = {
  elementId: string;
  elementType: string;
  profile: string | null;
  label: string;
  locationSubtitle: string;
  assemblyId: string | null;
  bracingPlane: BracingPlane | null;
  pairId: string | null;
  pairPrefix: string | null;
  groupKey: string | null;
  groupCount: number;
  isBracing: boolean;
  parentAssembly: ParentAssembly;
  gridX: string | null;
  gridZ: string | null;
  frameIndex: number | null;
  frameTrussed: boolean;
  trussType: string | null;
  defaultProfileScope: ProfileScope;
  highlightIds: string[];
  trussMemberCount: number;
  frameMemberCount: number;
};

export type SelectionActionId =
  | "change_profile"
  | "change_truss_type"
  | "switch_to_truss"
  | "switch_to_rafter"
  | "add_frame_like_this"
  | "delete_pair"
  | "delete_frame"
  | "add_brace_here"
  | "add_x_brace"
  | "ask_ai"
  | "more_remove";

export type SelectionActionTier = "primary" | "adjust" | "structure" | "more";

export type SelectionAction = {
  id: SelectionActionId;
  tier: SelectionActionTier;
  label: string;
  description?: string;
};

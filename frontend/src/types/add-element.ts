/** Panel-first add-element flow (no AI, no sketch). */

export type WallPanelSide = "A" | "B";
export type GableEnd = "near" | "far";

export type LongWallPanel = {
  kind: "long_wall";
  side: WallPanelSide;
  wallXLabel: string;
  bayIndex: number;
  zStart: string;
  zEnd: string;
  z0Mm: number;
  z1Mm: number;
  xMm: number;
  label: string;
};

export type GableWallPanel = {
  kind: "gable_wall";
  end: GableEnd;
  frameIndex: number;
  frameZ: string;
  xBayIndex: number;
  xStart: string;
  xEnd: string;
  x0Mm: number;
  x1Mm: number;
  zMm: number;
  label: string;
};

export type BracingPanel = LongWallPanel | GableWallPanel;

/** @deprecated use BracingPanel */
export type WallPanel = BracingPanel;

export type AddBracingScope =
  | "this_panel"
  | "all_bays_wall"
  | "both_walls"
  | "parallel_bay"
  | "portal_bay";

export type AddBracingStep = "pick_panel" | "profile" | "scope";

export type AddElementSession = {
  type: "bracing";
  step: AddBracingStep;
  panel: BracingPanel | null;
  profile: string;
};

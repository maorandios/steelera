/** Virtual grid selection — bays and frames, not steel members. */

export type GridSelectionKind = "bay" | "frame";

export type GridSelectionContext = {
  kind: GridSelectionKind;
  /** Stable id e.g. grid:bay:1 or grid:frame:2 */
  gridId: string;
  label: string;
  subtitle: string;
  bayIndex: number | null;
  frameIndex: number | null;
  /** Z axis labels (frame numbers as strings). */
  zStart: string;
  zEnd: string;
  xLabels: string[];
  defaultColumnProfile: string;
  defaultTieProfile: string;
};

export type GridPlacementContext = {
  x_spans: number[];
  z_spans: number[];
  height_mm: number;
  roof_pitch_deg: number;
  roof_style: string;
  mono_high_side: string;
};

export type GroundPlacementNode = {
  id: string;
  x: number;
  y: number;
  z: number;
  x_axis: string;
  z_axis: string;
  offset_mm: Record<string, number>;
  label: string;
  kind: string;
  connect_to: "auto" | "truss_bc" | "eave" | string;
};

export type ColumnPickMode = {
  profile: string;
  tieProfile: string;
  addTieInBay: boolean;
  bayZStart: string;
  bayZEnd: string;
};

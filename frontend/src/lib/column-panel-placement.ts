import {
  buildGableWallPanelsFromColumns,
  buildLongWallPanelsFromColumns,
  xPanelGridRefs,
  zPanelGridRefs,
} from "@/lib/bracing-panel-layout";
import { midBayZLabel } from "@/lib/grid-selection";
import { buildRoofPanels } from "@/lib/roof-panel-layout";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";
import {
  oppositeRoofSlope,
  oppositeSideWallLabel,
} from "@/lib/wall-panel";
import type {
  AddColumnScope,
  ColumnBayPosition,
  ColumnConnectTo,
  ColumnPanel,
  GableWallPanel,
  LongWallPanel,
  RoofPanel,
} from "@/types/add-element";
import type { ProjectElementMm } from "@/types/project";

export const COLUMN_WALL_POSITION_OPTIONS: {
  id: ColumnBayPosition;
  fraction: number;
  label: string;
  detail: string;
}[] = [
  {
    id: "start",
    fraction: 0,
    label: "Start",
    detail: "At the start frame of the bay",
  },
  {
    id: "third",
    fraction: 1 / 3,
    label: "33%",
    detail: "One-third along the bay length",
  },
  {
    id: "middle",
    fraction: 0.5,
    label: "Middle",
    detail: "Mid-bay between frames",
  },
  {
    id: "two_thirds",
    fraction: 2 / 3,
    label: "66%",
    detail: "Two-thirds along the bay length",
  },
  {
    id: "end",
    fraction: 1,
    label: "End",
    detail: "At the end frame of the bay",
  },
];

export const COLUMN_TRUSS_POSITION_OPTIONS: {
  id: ColumnBayPosition;
  fraction: number;
  label: string;
  detail: string;
}[] = [
  {
    id: "start",
    fraction: 0,
    label: "Eave",
    detail: "Under the truss at the eave panel node",
  },
  {
    id: "third",
    fraction: 1 / 3,
    label: "33%",
    detail: "One-third along the truss from eave to ridge",
  },
  {
    id: "middle",
    fraction: 0.5,
    label: "Middle",
    detail: "Mid-span along the truss chord",
  },
  {
    id: "two_thirds",
    fraction: 2 / 3,
    label: "66%",
    detail: "Two-thirds along the truss from eave to ridge",
  },
  {
    id: "end",
    fraction: 1,
    label: "Ridge",
    detail: "Under the truss at the ridge panel node",
  },
];

function fractionForPosition(position: ColumnBayPosition): number {
  return (
    COLUMN_TRUSS_POSITION_OPTIONS.find((o) => o.id === position)?.fraction ??
    COLUMN_WALL_POSITION_OPTIONS.find((o) => o.id === position)?.fraction ??
    0.5
  );
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function zAxisAtFraction(
  z0Mm: number,
  z1Mm: number,
  position: ColumnBayPosition,
  grid: StructuralGridState,
): string {
  if (position === "start") {
    const [z] = zPanelGridRefs(z0Mm, z0Mm, grid);
    return z;
  }
  if (position === "end") {
    const [z] = zPanelGridRefs(z1Mm, z1Mm, grid);
    return z;
  }
  if (position === "middle") {
    const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);
    return midBayZLabel(zStart, zEnd);
  }
  const fraction = fractionForPosition(position);
  const zMm = lerp(z0Mm, z1Mm, fraction);
  const [z] = zPanelGridRefs(zMm, zMm, grid);
  return z;
}

function xAxisAtFraction(
  x0Mm: number,
  x1Mm: number,
  position: ColumnBayPosition,
  grid: StructuralGridState,
): string {
  if (position === "start") {
    const [x] = xPanelGridRefs(x0Mm, x0Mm, grid);
    return x;
  }
  if (position === "end") {
    const [x] = xPanelGridRefs(x1Mm, x1Mm, grid);
    return x;
  }
  const fraction = fractionForPosition(position);
  const xMm = lerp(x0Mm, x1Mm, fraction);
  const [x] = xPanelGridRefs(xMm, xMm, grid);
  return x;
}

export type ColumnPlacementRequest = {
  x_axis: string;
  z_axis: string;
  connect_to: ColumnConnectTo;
  tie_location?: ColumnBayPosition;
  slope_side?: "left" | "right" | "mono";
  placement_label: string;
};

function singleColumnPlacement(
  panel: ColumnPanel,
  position: ColumnBayPosition,
  connectTo: ColumnConnectTo,
  grid: StructuralGridState,
): ColumnPlacementRequest {
  if (panel.kind === "long_wall") {
    return {
      x_axis: panel.wallXLabel,
      z_axis: zAxisAtFraction(panel.z0Mm, panel.z1Mm, position, grid),
      connect_to: connectTo,
      placement_label: `${panel.wallXLabel}-${position}`,
    };
  }

  if (panel.kind === "gable_wall") {
    return {
      x_axis: xAxisAtFraction(panel.x0Mm, panel.x1Mm, position, grid),
      z_axis: panel.frameZ,
      connect_to: connectTo,
      placement_label: `${panel.frameZ}-${position}`,
    };
  }

  return {
    x_axis: "",
    z_axis: panel.zStart,
    connect_to: connectTo,
    tie_location: position,
    slope_side: panel.slopeSide,
    placement_label: `${panel.slopeSide}-${panel.zStart}-${position}`,
  };
}

function longWallPanelsForScope(
  base: LongWallPanel,
  scope: AddColumnScope,
  grid: StructuralGridState,
  elements: ProjectElementMm[],
): LongWallPanel[] {
  const all = buildLongWallPanelsFromColumns(elements, grid);
  if (scope === "this_panel") {
    return [base];
  }
  const sameWall = all.filter((p) => p.wallXLabel === base.wallXLabel);
  if (scope === "all_bays_wall") {
    return sameWall;
  }
  if (scope === "both_walls") {
    const opposite = oppositeSideWallLabel(base.wallXLabel, grid);
    if (!opposite) {
      return sameWall;
    }
    return all.filter(
      (p) => p.wallXLabel === base.wallXLabel || p.wallXLabel === opposite,
    );
  }
  return [base];
}

function gablePanelsForScope(
  base: GableWallPanel,
  scope: AddColumnScope,
  grid: StructuralGridState,
  elements: ProjectElementMm[],
): GableWallPanel[] {
  const all = buildGableWallPanelsFromColumns(elements, grid);
  if (scope === "this_panel") {
    return [base];
  }
  const sameFrame = all.filter((p) => p.frameZ === base.frameZ);
  if (scope === "all_bays_wall") {
    return sameFrame;
  }
  return [base];
}

function roofPanelsForScope(
  base: RoofPanel,
  scope: AddColumnScope,
  grid: StructuralGridState,
  roofParams: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  >,
): RoofPanel[] {
  const allRoof = buildRoofPanels(grid, roofParams);
  if (scope === "this_panel") {
    return [base];
  }
  const otherSlope = oppositeRoofSlope(base.slopeSide);
  const sameSlope = allRoof.filter((p) => p.slopeSide === base.slopeSide);
  if (scope === "all_bays_slope") {
    return sameSlope;
  }
  if (scope === "parallel_slope") {
    if (!otherSlope) {
      return [base];
    }
    return allRoof.filter(
      (p) =>
        p.bayIndex === base.bayIndex &&
        (p.slopeSide === base.slopeSide || p.slopeSide === otherSlope),
    );
  }
  if (otherSlope) {
    return allRoof.filter(
      (p) => p.slopeSide === base.slopeSide || p.slopeSide === otherSlope,
    );
  }
  return allRoof;
}

export function resolveColumnPlacementsWithScope(
  panel: ColumnPanel,
  position: ColumnBayPosition,
  scope: AddColumnScope,
  connectTo: ColumnConnectTo,
  grid: StructuralGridState,
  elements: ProjectElementMm[],
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): ColumnPlacementRequest[] {
  if (panel.kind === "long_wall") {
    return longWallPanelsForScope(panel, scope, grid, elements).map((p) =>
      singleColumnPlacement(p, position, connectTo, grid),
    );
  }
  if (panel.kind === "gable_wall") {
    return gablePanelsForScope(panel, scope, grid, elements).map((p) =>
      singleColumnPlacement(p, position, connectTo, grid),
    );
  }
  if (!roofParams) {
    return [singleColumnPlacement(panel, position, connectTo, grid)];
  }
  return roofPanelsForScope(panel, scope, grid, roofParams).map((p) =>
    singleColumnPlacement(p, position, connectTo, grid),
  );
}

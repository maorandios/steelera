import { xPanelGridRefs } from "@/lib/bracing-panel-layout";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { TieBeamLocation, TieBeamPanel } from "@/types/add-element";

export type { TieBeamLocation };

export const TIE_BEAM_LOCATION_OPTIONS: {
  id: TieBeamLocation;
  fraction: number;
  label: string;
  detail: string;
}[] = [
  {
    id: "start",
    fraction: 0,
    label: "Start",
    detail: "Bottom of column (ground)",
  },
  {
    id: "third",
    fraction: 0.33,
    label: "33%",
    detail: "One-third up the column height",
  },
  {
    id: "middle",
    fraction: 0.5,
    label: "Middle",
    detail: "Mid-height between columns",
  },
  {
    id: "two_thirds",
    fraction: 0.66,
    label: "66%",
    detail: "Two-thirds up the column height",
  },
  {
    id: "end",
    fraction: 1,
    label: "End",
    detail: "Top of column (eave)",
  },
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function fractionForLocation(location: TieBeamLocation): number {
  return (
    TIE_BEAM_LOCATION_OPTIONS.find((opt) => opt.id === location)?.fraction ?? 0.5
  );
}

/** Elevation token along column height (ground → eave). */
function columnHeightElevation(location: TieBeamLocation): string {
  switch (location) {
    case "start":
      return "ground";
    case "third":
      return "ground+1/3";
    case "middle":
      return "ground+1/2";
    case "two_thirds":
      return "ground+2/3";
    case "end":
      return "eave";
    default:
      return "ground+1/2";
  }
}

/** Elevation along roof slope (eave → roof at X) for truss top-chord ties. */
function roofSlopeElevation(location: TieBeamLocation): string {
  switch (location) {
    case "start":
      return "eave";
    case "third":
      return "eave+1/3";
    case "middle":
      return "eave+1/2";
    case "two_thirds":
      return "eave+2/3";
    case "end":
      return "roof";
    default:
      return "eave+1/2";
  }
}

function xAxisAtFraction(
  x0Mm: number,
  x1Mm: number,
  fraction: number,
  grid: StructuralGridState,
): string {
  const xMm = lerp(x0Mm, x1Mm, fraction);
  const [xAxis] = xPanelGridRefs(xMm, xMm, grid);
  return xAxis;
}

export type TieBeamPlacementRequest = {
  orientation: "along_z" | "along_x";
  x_axis?: string;
  z_start?: string;
  z_end?: string;
  z_axis?: string;
  x_start?: string;
  x_end?: string;
  elevation: string;
};

export function resolveTieBeamPlacement(
  panel: TieBeamPanel,
  location: TieBeamLocation,
  grid: StructuralGridState,
): TieBeamPlacementRequest {
  const fraction = fractionForLocation(location);

  if (panel.kind === "long_wall") {
    return {
      orientation: "along_z",
      x_axis: panel.wallXLabel,
      z_start: panel.zStart,
      z_end: panel.zEnd,
      elevation: columnHeightElevation(location),
    };
  }

  if (panel.kind === "gable_wall") {
    return {
      orientation: "along_x",
      z_axis: panel.frameZ,
      x_start: panel.xStart,
      x_end: panel.xEnd,
      elevation: columnHeightElevation(location),
    };
  }

  const xAxis = xAxisAtFraction(panel.x0Mm, panel.x1Mm, fraction, grid);
  return {
    orientation: "along_z",
    x_axis: xAxis,
    z_start: panel.zStart,
    z_end: panel.zEnd,
    elevation:
      panel.kind === "truss_tc"
        ? roofSlopeElevation(location)
        : columnHeightElevation(location),
  };
}

import { xPanelGridRefs } from "@/lib/bracing-panel-layout";
import { buildRoofPanels } from "@/lib/roof-panel-layout";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";
import { oppositeRoofSlope } from "@/lib/wall-panel";
import { trussChordXStationsInSpan } from "@/lib/truss-panel-layout";
import type {
  AddTieBeamScope,
  RoofPanel,
  TieBeamChord,
  TieBeamLocation,
  TieBeamPanel,
} from "@/types/add-element";import type { ProjectElementMm } from "@/types/project";

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
    fraction: 1 / 3,
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
    fraction: 2 / 3,
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

export const TIE_BEAM_TRUSS_LOCATION_OPTIONS: {
  id: TieBeamLocation;
  fraction: number;
  label: string;
  detail: string;
}[] = [
  {
    id: "start",
    fraction: 0,
    label: "Eave",
    detail: "At the eave heel of the truss chord",
  },
  {
    id: "third",
    fraction: 1 / 3,
    label: "33%",
    detail: "One-third along the chord from eave to ridge",
  },
  {
    id: "middle",
    fraction: 0.5,
    label: "Middle",
    detail: "Mid-span along the chord from eave to ridge",
  },
  {
    id: "two_thirds",
    fraction: 2 / 3,
    label: "66%",
    detail: "Two-thirds along the chord from eave to ridge",
  },
  {
    id: "end",
    fraction: 1,
    label: "Ridge",
    detail: "At the ridge / apex of the truss chord",
  },
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function fractionForLocation(location: TieBeamLocation): number {
  return (
    TIE_BEAM_TRUSS_LOCATION_OPTIONS.find((opt) => opt.id === location)
      ?.fraction ??
    TIE_BEAM_LOCATION_OPTIONS.find((opt) => opt.id === location)?.fraction ??
    0.5
  );
}

function columnFractionForLocation(location: TieBeamLocation): number {
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

function xAxisAtMm(xMm: number, grid: StructuralGridState): string {
  const [xAxis] = xPanelGridRefs(xMm, xMm, grid);
  return xAxis;
}

type RoofPanelSpan = {
  eaveX: number;
  ridgeX: number;
  eaveElevation: string;
  ridgeElevation: string;
};

function roofPanelSpan(panel: RoofPanel): RoofPanelSpan {
  if (panel.elevStart === "eave") {
    return {
      eaveX: panel.x0Mm,
      ridgeX: panel.x1Mm,
      eaveElevation: "eave",
      ridgeElevation: panel.elevEnd,
    };
  }
  if (panel.elevEnd === "eave") {
    return {
      eaveX: panel.x1Mm,
      ridgeX: panel.x0Mm,
      eaveElevation: "eave",
      ridgeElevation: panel.elevStart,
    };
  }
  return {
    eaveX: panel.x0Mm,
    ridgeX: panel.x1Mm,
    eaveElevation: panel.elevStart,
    ridgeElevation: panel.elevEnd,
  };
}

function orderEaveToRidge(
  stations: number[],
  eaveX: number,
  ridgeX: number,
): number[] {
  const sorted = [...stations].sort((a, b) => a - b);
  if (Math.abs(sorted[0] - eaveX) <= Math.abs(sorted[0] - ridgeX)) {
    return sorted;
  }
  return sorted.reverse();
}

function xAtRoofTieLocation(
  elements: ProjectElementMm[],
  chord: "tc" | "bc",
  span: RoofPanelSpan,
  location: TieBeamLocation,
  grid: StructuralGridState,
): string {
  if (location === "start") {
    return xAxisAtMm(span.eaveX, grid);
  }
  if (location === "end") {
    return xAxisAtMm(span.ridgeX, grid);
  }

  const fraction = fractionForLocation(location);
  const stations = trussChordXStationsInSpan(
    elements,
    chord,
    span.eaveX,
    span.ridgeX,
  );

  if (stations.length > 2) {
    const fromEave = orderEaveToRidge(stations, span.eaveX, span.ridgeX);
    const idx = Math.round(fraction * (fromEave.length - 1));
    const xMm = fromEave[Math.max(0, Math.min(fromEave.length - 1, idx))];
    return xAxisAtMm(xMm, grid);
  }

  return xAxisAtMm(lerp(span.eaveX, span.ridgeX, fraction), grid);
}

function roofTieElevation(
  span: RoofPanelSpan,
  chord: "tc" | "bc",
  location: TieBeamLocation,
): string {
  if (chord === "bc") {
    return "eave";
  }
  if (location === "start") {
    return span.eaveElevation;
  }
  if (location === "end") {
    return span.ridgeElevation;
  }
  return "roof";
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
  placement_label: string;
  truss_chord?: "tc" | "bc";
  truss_type?: string;
  slope_side?: "left" | "right" | "mono";
  tie_location?: TieBeamLocation;
};

export function resolveTieBeamPlacements(
  panel: TieBeamPanel,
  location: TieBeamLocation,
  grid: StructuralGridState,
  chord: TieBeamChord | null,
  elements: ProjectElementMm[] = [],
): TieBeamPlacementRequest[] {
  if (panel.kind === "long_wall") {
    return [
      {
        orientation: "along_z",
        x_axis: panel.wallXLabel,
        z_start: panel.zStart,
        z_end: panel.zEnd,
        elevation: columnHeightElevation(location),
        placement_label: location,
      },
    ];
  }

  if (panel.kind === "gable_wall") {
    return [
      {
        orientation: "along_x",
        z_axis: panel.frameZ,
        x_start: panel.xStart,
        x_end: panel.xEnd,
        elevation: columnHeightElevation(location),
        placement_label: location,
      },
    ];
  }

  if (panel.kind === "roof") {
    const span = roofPanelSpan(panel);
    const chords: Array<"tc" | "bc"> =
      chord === "both" ? ["tc", "bc"] : [chord === "bc" ? "bc" : "tc"];
    return chords.map((ch) => ({
      orientation: "along_z" as const,
      z_start: panel.zStart,
      z_end: panel.zEnd,
      elevation: roofTieElevation(span, ch, location),
      placement_label: `${location}-${ch}`,
      truss_chord: ch,
      tie_location: location,
      slope_side: panel.slopeSide,
    }));
  }

  const fraction = columnFractionForLocation(location);
  const xAxis = xAxisAtMm(
    lerp(panel.x0Mm, panel.x1Mm, fraction),
    grid,
  );
  const legacyChord: "tc" | "bc" = panel.kind === "truss_tc" ? "tc" : "bc";
  const span = {
    eaveX: panel.x0Mm,
    ridgeX: panel.x1Mm,
    eaveElevation: "eave",
    ridgeElevation: legacyChord === "tc" ? "roof" : "eave",
  };
  return [
    {
      orientation: "along_z",
      x_axis: xAtRoofTieLocation(elements, legacyChord, span, location, grid),
      z_start: panel.zStart,
      z_end: panel.zEnd,
      elevation: roofTieElevation(span, legacyChord, location),
      placement_label: `${location}-${legacyChord}`,
    },
  ];
}

/** @deprecated use resolveTieBeamPlacements */
export function resolveTieBeamPlacement(
  panel: TieBeamPanel,
  location: TieBeamLocation,
  grid: StructuralGridState,
  chord: TieBeamChord | null = null,
  elements: ProjectElementMm[] = [],
): TieBeamPlacementRequest {
  return resolveTieBeamPlacements(panel, location, grid, chord, elements)[0];
}

function roofPanelsForScope(
  base: RoofPanel,
  scope: AddTieBeamScope,
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

export function resolveTieBeamPlacementsWithScope(
  panel: TieBeamPanel,
  location: TieBeamLocation,
  scope: AddTieBeamScope,
  grid: StructuralGridState,
  chord: TieBeamChord | null,
  elements: ProjectElementMm[] = [],
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): TieBeamPlacementRequest[] {
  if (panel.kind !== "roof" || !roofParams) {
    return resolveTieBeamPlacements(panel, location, grid, chord, elements);
  }

  const panels = roofPanelsForScope(panel, scope, grid, roofParams);
  return panels.flatMap((p) =>
    resolveTieBeamPlacements(p, location, grid, chord, elements),
  );
}

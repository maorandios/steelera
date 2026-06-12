import { xPanelGridRefs, zPanelGridRefs } from "@/lib/bracing-panel-layout";
import { gridLineLetter, gridLineNumber } from "@/lib/structural-grid";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";
import {
  computeRoofGeometry,
  roofSlopeSegments,
} from "@/lib/roof-panel-layout";
import type {
  BracingPanel,
  GableEnd,
  GableWallPanel,
  LongWallPanel,
  PickablePanel,
  RoofPanel,
  RoofSlopeSide,
  TieBeamPanel,
  ColumnPanel,
  TrussBcPanel,
  TrussTcPanel,
  WallPanelSide,
} from "@/types/add-element";
export function pickPanelKey(panel: PickablePanel): string {
  if (panel.kind === "long_wall") {
    return `long:${panel.wallXLabel}:${panel.z0Mm}:${panel.z1Mm}`;
  }
  if (panel.kind === "roof") {
    return `roof:${panel.slopeSide}:${panel.z0Mm}:${panel.z1Mm}`;
  }
  if (panel.kind === "truss_tc") {
    return `truss-tc:${panel.z0Mm}:${panel.z1Mm}:${panel.x0Mm}:${panel.x1Mm}`;
  }
  if (panel.kind === "truss_bc") {
    return `truss-bc:${panel.z0Mm}:${panel.z1Mm}:${panel.x0Mm}:${panel.x1Mm}`;
  }
  return `gable:${panel.end}:${panel.x0Mm}:${panel.x1Mm}`;
}

export function bracingPanelKey(panel: BracingPanel): string {
  return pickPanelKey(panel);
}
/** @deprecated use bracingPanelKey */
export const wallPanelKey = bracingPanelKey;

export function longWallPanelFromPick(
  side: WallPanelSide,
  wallXLabel: string,
  bayIndex: number,
  z0Mm: number,
  z1Mm: number,
  xMm: number,
  grid: StructuralGridState,
): LongWallPanel {
  const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);
  return {
    kind: "long_wall",
    side,
    wallXLabel,
    bayIndex,
    zStart,
    zEnd,
    z0Mm,
    z1Mm,
    xMm,
    label: `Wall ${wallXLabel} · Bay ${zStart} → ${zEnd}`,
  };
}

export function gableWallPanelFromPick(
  end: GableEnd,
  frameIndex: number,
  xBayIndex: number,
  x0Mm: number,
  x1Mm: number,
  zMm: number,
  grid: StructuralGridState,
): GableWallPanel {
  const [xStart, xEnd] = xPanelGridRefs(x0Mm, x1Mm, grid);
  const frameZ = gridLineNumber(frameIndex);
  const endLabel = end === "near" ? "Near gable" : "Far gable";
  return {
    kind: "gable_wall",
    end,
    frameIndex,
    frameZ,
    xBayIndex,
    xStart,
    xEnd,
    x0Mm,
    x1Mm,
    zMm,
    label: `${endLabel} · ${xStart} → ${xEnd} · Frame ${frameZ}`,
  };
}

export function roofPanelFromPick(
  slopeSide: RoofSlopeSide,
  slopeIndex: number,
  bayIndex: number,
  z0Mm: number,
  z1Mm: number,
  grid: StructuralGridState,
  params: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  >,
): RoofPanel | null {
  const roof = computeRoofGeometry(grid, params);
  if (!roof) return null;
  const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);
  const slope = roofSlopeSegments(grid, roof).find(
    (entry) => entry.slopeSide === slopeSide && entry.slopeIndex === slopeIndex,
  );
  if (!slope) return null;
  const slopeLabel =
    slope.slopeSide === "left"
      ? "Left slope"
      : slope.slopeSide === "right"
        ? "Right slope"
        : "Roof slope";
  return {
    kind: "roof",
    slopeSide: slope.slopeSide,
    slopeIndex: slope.slopeIndex,
    bayIndex,
    zStart,
    zEnd,
    z0Mm,
    z1Mm,
    xStart: slope.xStart,
    xEnd: slope.xEnd,
    x0Mm: slope.x0Mm,
    x1Mm: slope.x1Mm,
    elevStart: slope.elevStart,
    elevEnd: slope.elevEnd,
    label: `${slopeLabel} · Frame ${zStart} → ${zEnd}`,
  };
}

export type WallPanelPickData = {
  panelKind?: string;
  side?: WallPanelSide;
  wallXLabel?: string;
  bayIndex?: number;
  z0Mm?: number;
  z1Mm?: number;
  xMm?: number;
  gableEnd?: GableEnd;
  frameIndex?: number;
  xBayIndex?: number;
  x0Mm?: number;
  x1Mm?: number;
  zMm?: number;
  slopeSide?: RoofSlopeSide;
  slopeIndex?: number;
  roofBayIndex?: number;
  trussChord?: "tc" | "bc";
  trussZBayIndex?: number;
  trussXPanelIndex?: number;
};

function trussPanelFromPick(
  chord: "tc" | "bc",
  zBayIndex: number,
  xPanelIndex: number,
  z0Mm: number,
  z1Mm: number,
  x0Mm: number,
  x1Mm: number,
  grid: StructuralGridState,
): TrussTcPanel | TrussBcPanel | null {
  const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);
  const [xStart, xEnd] = xPanelGridRefs(x0Mm, x1Mm, grid);
  const xCenter = (x0Mm + x1Mm) / 2;
  const [xAxis] = xPanelGridRefs(xCenter, xCenter, grid);
  const chordLabel = chord === "tc" ? "TC truss" : "BC truss";
  const base = {
    zBayIndex,
    zStart,
    zEnd,
    z0Mm,
    z1Mm,
    xPanelIndex,
    xStart,
    xEnd,
    x0Mm,
    x1Mm,
    xAxis,
    label: `${chordLabel} · ${xStart} → ${xEnd} · Frame ${zStart} → ${zEnd}`,
  };
  if (chord === "tc") {
    return { kind: "truss_tc", ...base, elevation: "roof" as const };
  }
  return { kind: "truss_bc", ...base, elevation: "eave" as const };
}

export function columnPanelFromPickData(
  data: WallPanelPickData,
  grid: StructuralGridState,
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): ColumnPanel | null {
  if (data.panelKind === "roof") {
    if (
      (data.slopeSide !== "left" &&
        data.slopeSide !== "right" &&
        data.slopeSide !== "mono") ||
      typeof data.slopeIndex !== "number" ||
      typeof data.roofBayIndex !== "number" ||
      typeof data.z0Mm !== "number" ||
      typeof data.z1Mm !== "number" ||
      !roofParams
    ) {
      return null;
    }
    return roofPanelFromPick(
      data.slopeSide,
      data.slopeIndex,
      data.roofBayIndex,
      data.z0Mm,
      data.z1Mm,
      grid,
      roofParams,
    );
  }
  if (data.panelKind === "gable_wall") {
    if (
      (data.gableEnd !== "near" && data.gableEnd !== "far") ||
      typeof data.frameIndex !== "number" ||
      typeof data.xBayIndex !== "number" ||
      typeof data.x0Mm !== "number" ||
      typeof data.x1Mm !== "number" ||
      typeof data.zMm !== "number"
    ) {
      return null;
    }
    return gableWallPanelFromPick(
      data.gableEnd,
      data.frameIndex,
      data.xBayIndex,
      data.x0Mm,
      data.x1Mm,
      data.zMm,
      grid,
    );
  }
  if (
    (data.side !== "A" && data.side !== "B") ||
    typeof data.wallXLabel !== "string" ||
    typeof data.bayIndex !== "number" ||
    typeof data.z0Mm !== "number" ||
    typeof data.z1Mm !== "number" ||
    typeof data.xMm !== "number"
  ) {
    return null;
  }
  return longWallPanelFromPick(
    data.side,
    data.wallXLabel,
    data.bayIndex,
    data.z0Mm,
    data.z1Mm,
    data.xMm,
    grid,
  );
}

export function tiePanelFromPickData(
  data: WallPanelPickData,
  grid: StructuralGridState,
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): TieBeamPanel | null {
  if (data.panelKind === "roof") {
    if (
      (data.slopeSide !== "left" &&
        data.slopeSide !== "right" &&
        data.slopeSide !== "mono") ||
      typeof data.slopeIndex !== "number" ||
      typeof data.roofBayIndex !== "number" ||
      typeof data.z0Mm !== "number" ||
      typeof data.z1Mm !== "number" ||
      !roofParams
    ) {
      return null;
    }
    return roofPanelFromPick(
      data.slopeSide,
      data.slopeIndex,
      data.roofBayIndex,
      data.z0Mm,
      data.z1Mm,
      grid,
      roofParams,
    );
  }
  if (data.panelKind === "truss_tc" || data.panelKind === "truss_bc") {
    const chord = data.panelKind === "truss_tc" ? "tc" : "bc";
    if (
      typeof data.trussZBayIndex !== "number" ||
      typeof data.trussXPanelIndex !== "number" ||
      typeof data.z0Mm !== "number" ||
      typeof data.z1Mm !== "number" ||
      typeof data.x0Mm !== "number" ||
      typeof data.x1Mm !== "number"
    ) {
      return null;
    }
    return trussPanelFromPick(
      chord,
      data.trussZBayIndex,
      data.trussXPanelIndex,
      data.z0Mm,
      data.z1Mm,
      data.x0Mm,
      data.x1Mm,
      grid,
    );
  }
  if (data.panelKind === "gable_wall") {
    if (
      (data.gableEnd !== "near" && data.gableEnd !== "far") ||
      typeof data.frameIndex !== "number" ||
      typeof data.xBayIndex !== "number" ||
      typeof data.x0Mm !== "number" ||
      typeof data.x1Mm !== "number" ||
      typeof data.zMm !== "number"
    ) {
      return null;
    }
    return gableWallPanelFromPick(
      data.gableEnd,
      data.frameIndex,
      data.xBayIndex,
      data.x0Mm,
      data.x1Mm,
      data.zMm,
      grid,
    );
  }
  if (
    (data.side !== "A" && data.side !== "B") ||
    typeof data.wallXLabel !== "string" ||
    typeof data.bayIndex !== "number" ||
    typeof data.z0Mm !== "number" ||
    typeof data.z1Mm !== "number" ||
    typeof data.xMm !== "number"
  ) {
    return null;
  }
  return longWallPanelFromPick(
    data.side,
    data.wallXLabel,
    data.bayIndex,
    data.z0Mm,
    data.z1Mm,
    data.xMm,
    grid,
  );
}

export function bracingPanelFromPickData(
  data: WallPanelPickData,
  grid: StructuralGridState,
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null,
): BracingPanel | null {
  if (data.panelKind === "roof") {
    if (
      (data.slopeSide !== "left" &&
        data.slopeSide !== "right" &&
        data.slopeSide !== "mono") ||
      typeof data.slopeIndex !== "number" ||
      typeof data.roofBayIndex !== "number" ||
      typeof data.z0Mm !== "number" ||
      typeof data.z1Mm !== "number" ||
      !roofParams
    ) {
      return null;
    }
    return roofPanelFromPick(
      data.slopeSide,
      data.slopeIndex,
      data.roofBayIndex,
      data.z0Mm,
      data.z1Mm,
      grid,
      roofParams,
    );
  }
  if (data.panelKind === "gable_wall") {
    if (
      (data.gableEnd !== "near" && data.gableEnd !== "far") ||
      typeof data.frameIndex !== "number" ||
      typeof data.xBayIndex !== "number" ||
      typeof data.x0Mm !== "number" ||
      typeof data.x1Mm !== "number" ||
      typeof data.zMm !== "number"
    ) {
      return null;
    }
    return gableWallPanelFromPick(
      data.gableEnd,
      data.frameIndex,
      data.xBayIndex,
      data.x0Mm,
      data.x1Mm,
      data.zMm,
      grid,
    );
  }
  if (
    (data.side !== "A" && data.side !== "B") ||
    typeof data.wallXLabel !== "string" ||
    typeof data.bayIndex !== "number" ||
    typeof data.z0Mm !== "number" ||
    typeof data.z1Mm !== "number" ||
    typeof data.xMm !== "number"
  ) {
    return null;
  }
  return longWallPanelFromPick(
    data.side,
    data.wallXLabel,
    data.bayIndex,
    data.z0Mm,
    data.z1Mm,
    data.xMm,
    grid,
  );
}

export function sideWallLabels(grid: StructuralGridState): {
  sideA: string;
  sideB: string;
} {
  const xCount = grid.xCoordsMm.length;
  const sideA = gridLineLetter(0);
  const sideB = gridLineLetter(Math.max(0, xCount - 1));
  return { sideA, sideB };
}

export function oppositeSideWallLabel(
  wallXLabel: string,
  grid: StructuralGridState,
): string | null {
  const { sideA, sideB } = sideWallLabels(grid);
  if (wallXLabel === sideA) return sideB;
  if (wallXLabel === sideB) return sideA;
  return null;
}

export function oppositeGableEnd(end: GableEnd): GableEnd {
  return end === "near" ? "far" : "near";
}

export function oppositeRoofSlope(
  slopeSide: RoofSlopeSide,
): RoofSlopeSide | null {
  if (slopeSide === "left") return "right";
  if (slopeSide === "right") return "left";
  return null;
}

export function defaultBracingProfile(
  elements: { element_type?: string | null; profile_name?: string | null }[],
): string {
  const hit = elements.find(
    (e) => e.element_type === "bracing" && e.profile_name,
  );
  return hit?.profile_name ?? "L60x60x6";
}

export function defaultTieBeamProfile(
  elements: { element_type?: string | null; profile_name?: string | null }[],
): string {
  const hit = elements.find(
    (e) => e.element_type === "tie_beam" && e.profile_name,
  );
  return hit?.profile_name ?? "IPE200";
}

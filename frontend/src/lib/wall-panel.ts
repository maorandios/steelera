import { gridLineLetter, gridLineNumber } from "@/lib/structural-grid";
import type { StructuralGridState } from "@/lib/structural-grid";
import type {
  BracingPanel,
  GableEnd,
  GableWallPanel,
  LongWallPanel,
  WallPanelSide,
} from "@/types/add-element";

export function bracingPanelKey(panel: BracingPanel): string {
  if (panel.kind === "long_wall") {
    return `long:${panel.wallXLabel}:${panel.z0Mm}:${panel.z1Mm}`;
  }
  return `gable:${panel.end}:${panel.x0Mm}:${panel.x1Mm}`;
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
  const zStart = gridLineNumber(
    grid.zCoordsMm.findIndex((z) => Math.abs(z - z0Mm) < 300),
  );
  const zEnd = gridLineNumber(
    grid.zCoordsMm.findIndex((z) => Math.abs(z - z1Mm) < 300),
  );
  return {
    kind: "long_wall",
    side,
    wallXLabel,
    bayIndex,
    zStart: zStart === "?" ? String(bayIndex + 1) : zStart,
    zEnd: zEnd === "?" ? String(bayIndex + 2) : zEnd,
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
  const xStart = gridLineLetter(
    Math.max(
      0,
      grid.xCoordsMm.findIndex((x) => Math.abs(x - x0Mm) < 300),
    ),
  );
  const xEnd = gridLineLetter(
    Math.max(
      0,
      grid.xCoordsMm.findIndex((x) => Math.abs(x - x1Mm) < 300),
    ),
  );
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
};

export function bracingPanelFromPickData(
  data: WallPanelPickData,
  grid: StructuralGridState,
): BracingPanel | null {
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

export function defaultBracingProfile(
  elements: { element_type?: string | null; profile_name?: string | null }[],
): string {
  const hit = elements.find(
    (e) => e.element_type === "bracing" && e.profile_name,
  );
  return hit?.profile_name ?? "L60x60x6";
}

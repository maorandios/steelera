import { parseMemberId } from "@/lib/selection-id-parse";
import { gridLineLetter, gridLineNumber } from "@/lib/structural-grid";
import type { StructuralGridState } from "@/lib/structural-grid";
import { memberEndpointsMm } from "@/lib/memberFrame";
import { isColumnElement } from "@/lib/column-member-scope";
import type {
  BracingPanel,
  GableEnd,
  GableWallPanel,
  LongWallPanel,
} from "@/types/add-element";
import type { ProjectElementMm } from "@/types/project";

const TOL_MM = 300;

function footMm(
  element: ProjectElementMm,
): { x: number; y: number; z: number } | null {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;
  const foot = ep.start.y <= ep.end.y ? ep.start : ep.end;
  return { x: foot.x, y: foot.y, z: foot.z };
}

function clusterSorted(values: number[], tol = TOL_MM): number[] {
  const sorted = [...values].sort((a, b) => a - b);
  const out: number[] = [];
  for (const value of sorted) {
    if (!out.length || value - out[out.length - 1] > tol) {
      out.push(value);
    }
  }
  return out;
}

function isGablePostElement(element: ProjectElementMm): boolean {
  return /-gablepost-/i.test(element.id);
}

function mmToFractionalGridRef(
  valueMm: number,
  coords: number[],
  formatLabel: (index: number) => string,
): string {
  for (let i = 0; i < coords.length; i += 1) {
    if (Math.abs(coords[i] - valueMm) < TOL_MM) {
      return formatLabel(i);
    }
  }
  for (let i = 0; i < coords.length - 1; i += 1) {
    const a = coords[i];
    const b = coords[i + 1];
    if (valueMm < a - TOL_MM || valueMm > b + TOL_MM || b <= a) {
      continue;
    }
    const frac = (valueMm - a) / (b - a);
    const denom = 12;
    const num = Math.max(1, Math.min(denom - 1, Math.round(frac * denom)));
    if (frac * denom < 0.5) {
      return formatLabel(i);
    }
    if (frac * denom > denom - 0.5) {
      return formatLabel(i + 1);
    }
    return `${formatLabel(i)}+${num}/${denom}`;
  }
  const nearest = coords.reduce(
    (best, coord, index) => {
      const dist = Math.abs(coord - valueMm);
      return dist < best.dist ? { index, dist } : best;
    },
    { index: 0, dist: Infinity },
  );
  return formatLabel(nearest.index);
}

function xMmToGridRef(xMm: number, grid: StructuralGridState): string {
  return mmToFractionalGridRef(xMm, grid.xCoordsMm, gridLineLetter);
}

function zMmToGridRef(zMm: number, grid: StructuralGridState): string {
  return mmToFractionalGridRef(zMm, grid.zCoordsMm, gridLineNumber);
}

function longWallColumnZPositions(
  elements: ProjectElementMm[],
  wallLabel: string,
): number[] {
  const zValues: number[] = [];
  for (const element of elements) {
    if (!isColumnElement(element)) continue;
    const parsed = parseMemberId(element.id);
    if (parsed.gridX !== wallLabel) continue;
    const foot = footMm(element);
    if (foot) zValues.push(foot.z);
  }
  return clusterSorted(zValues);
}

function gableVerticalXPositions(
  elements: ProjectElementMm[],
  frameZ: string,
): number[] {
  const xValues: number[] = [];
  for (const element of elements) {
    const isGablePost = isGablePostElement(element);
    const isCol = isColumnElement(element);
    if (!isGablePost && !isCol) continue;

    const parsed = parseMemberId(element.id);
    const frameMatch =
      parsed.frameZ === frameZ ||
      (isGablePost && element.id.includes(`-gablepost-${frameZ}-`));
    if (!frameMatch) continue;

    const foot = footMm(element);
    if (foot) xValues.push(foot.x);
  }
  return clusterSorted(xValues);
}

function wallXPositionMm(
  wallLabel: string,
  grid: StructuralGridState,
): number | null {
  const idx = grid.xCoordsMm.findIndex(
    (_, i) => gridLineLetter(i) === wallLabel,
  );
  if (idx < 0) return null;
  return grid.xCoordsMm[idx];
}

export function buildLongWallPanelsFromColumns(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): LongWallPanel[] {
  const { sideA, sideB } = {
    sideA: gridLineLetter(0),
    sideB: gridLineLetter(Math.max(0, grid.xCoordsMm.length - 1)),
  };
  const walls: { side: "A" | "B"; label: string }[] = [
    { side: "A", label: sideA },
    { side: "B", label: sideB },
  ];
  const out: LongWallPanel[] = [];

  for (const wall of walls) {
    const xMm = wallXPositionMm(wall.label, grid);
    if (xMm == null) continue;
    const zPositions = longWallColumnZPositions(elements, wall.label);
    if (zPositions.length < 2) continue;

    for (let bayIndex = 0; bayIndex < zPositions.length - 1; bayIndex += 1) {
      const z0Mm = zPositions[bayIndex];
      const z1Mm = zPositions[bayIndex + 1];
      const zStart = zMmToGridRef(z0Mm, grid);
      const zEnd = zMmToGridRef(z1Mm, grid);
      out.push({
        kind: "long_wall",
        side: wall.side,
        wallXLabel: wall.label,
        bayIndex,
        zStart,
        zEnd,
        z0Mm,
        z1Mm,
        xMm,
        label: `Wall ${wall.label} · Bay ${zStart} → ${zEnd}`,
      });
    }
  }

  return out;
}

export function buildGableWallPanelsFromColumns(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): GableWallPanel[] {
  if (grid.zCoordsMm.length < 1 || grid.xCoordsMm.length < 2) {
    return [];
  }

  const ends: { end: GableEnd; frameIndex: number; zMm: number; frameZ: string }[] =
    [
      {
        end: "near",
        frameIndex: 0,
        zMm: grid.zCoordsMm[0],
        frameZ: gridLineNumber(0),
      },
      {
        end: "far",
        frameIndex: grid.zCoordsMm.length - 1,
        zMm: grid.zCoordsMm[grid.zCoordsMm.length - 1],
        frameZ: gridLineNumber(grid.zCoordsMm.length - 1),
      },
    ];

  const out: GableWallPanel[] = [];

  for (const gable of ends) {
    const xPositions = gableVerticalXPositions(elements, gable.frameZ);
    if (xPositions.length < 2) continue;

    for (let xBayIndex = 0; xBayIndex < xPositions.length - 1; xBayIndex += 1) {
      const x0Mm = xPositions[xBayIndex];
      const x1Mm = xPositions[xBayIndex + 1];
      const xStart = xMmToGridRef(x0Mm, grid);
      const xEnd = xMmToGridRef(x1Mm, grid);
      const endLabel = gable.end === "near" ? "Near gable" : "Far gable";
      out.push({
        kind: "gable_wall",
        end: gable.end,
        frameIndex: gable.frameIndex,
        frameZ: gable.frameZ,
        xBayIndex,
        xStart,
        xEnd,
        x0Mm,
        x1Mm,
        zMm: gable.zMm,
        label: `${endLabel} · ${xStart} → ${xEnd} · Frame ${gable.frameZ}`,
      });
    }
  }

  return out;
}

export function buildBracingPanelsFromColumns(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): BracingPanel[] {
  if (elements.length === 0) {
    return [];
  }
  return [
    ...buildLongWallPanelsFromColumns(elements, grid),
    ...buildGableWallPanelsFromColumns(elements, grid),
  ];
}

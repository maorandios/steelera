import { xPanelGridRefs, zPanelGridRefs } from "@/lib/bracing-panel-layout";
import { memberEndpointsMm } from "@/lib/memberFrame";
import { gridLineNumber } from "@/lib/structural-grid";
import type { StructuralGridState } from "@/lib/structural-grid";
import type {
  TrussBcPanel,
  TrussTcPanel,
} from "@/types/add-element";
import type { ProjectElementMm } from "@/types/project";

const TOL_MM = 300;
const FRAME_Z_TOL_MM = 200;

export type TrussPanelCornerMm = { x: number; y: number; z: number };

export type TrussSegment = {
  kind: "tc" | "bc";
  frameZ: string;
  start: TrussPanelCornerMm;
  end: TrussPanelCornerMm;
};

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

function parseTrussId(id: string): { kind: "tc" | "bc"; frameZ: string } | null {
  const match = id.match(/-truss-(tc|bc)-(\d+)-/i);
  if (!match) return null;
  return { kind: match[1].toLowerCase() as "tc" | "bc", frameZ: match[2] };
}

function isTrussChordElement(element: ProjectElementMm): boolean {
  const type = (element.element_type ?? "").toLowerCase();
  return type === "truss_chord" || /-truss-(tc|bc)-/i.test(element.id);
}

export function collectTrussSegments(
  elements: ProjectElementMm[],
): TrussSegment[] {
  const out: TrussSegment[] = [];
  for (const element of elements) {
    if (!isTrussChordElement(element)) continue;
    const parsed = parseTrussId(element.id);
    if (!parsed) continue;
    const endpoints = memberEndpointsMm(element);
    if (!endpoints) continue;
    out.push({
      kind: parsed.kind,
      frameZ: parsed.frameZ,
      start: {
        x: endpoints.start.x,
        y: endpoints.start.y,
        z: endpoints.start.z,
      },
      end: {
        x: endpoints.end.x,
        y: endpoints.end.y,
        z: endpoints.end.z,
      },
    });
  }
  return out;
}

function trussXLayout(segments: TrussSegment[], kind: "tc" | "bc"): number[] {
  const xs: number[] = [];
  for (const segment of segments) {
    if (segment.kind !== kind) continue;
    xs.push(segment.start.x, segment.end.x);
  }
  return clusterSorted(xs);
}

export function trussChordXStationsInSpan(
  elements: ProjectElementMm[],
  chord: "tc" | "bc",
  eaveX: number,
  ridgeX: number,
): number[] {
  const lo = Math.min(eaveX, ridgeX);
  const hi = Math.max(eaveX, ridgeX);
  const xs: number[] = [eaveX, ridgeX];
  for (const segment of collectTrussSegments(elements)) {
    if (segment.kind !== chord) continue;
    for (const x of [segment.start.x, segment.end.x]) {
      if (x >= lo - TOL_MM && x <= hi + TOL_MM) {
        xs.push(x);
      }
    }
  }
  return clusterSorted(xs);
}

export function hasTrussSegments(elements: ProjectElementMm[]): boolean {
  return collectTrussSegments(elements).length > 0;
}

function yOnChordAtX(
  segments: TrussSegment[],
  kind: "tc" | "bc",
  frameZMm: number,
  xMm: number,
): number {
  let bestY: number | null = null;
  let bestScore = Infinity;

  for (const segment of segments) {
    if (segment.kind !== kind) continue;
    for (const [a, b] of [
      [segment.start, segment.end] as const,
      [segment.end, segment.start] as const,
    ]) {
      if (Math.abs(a.z - frameZMm) > FRAME_Z_TOL_MM) continue;
      const score = Math.abs(a.x - xMm);
      if (score < bestScore) {
        bestScore = score;
        bestY = a.y;
      }
    }
    const { start: s, end: e } = segment;
    if (
      Math.abs(s.z - frameZMm) > FRAME_Z_TOL_MM &&
      Math.abs(e.z - frameZMm) > FRAME_Z_TOL_MM
    ) {
      continue;
    }
    const lo = Math.min(s.x, e.x);
    const hi = Math.max(s.x, e.x);
    if (xMm < lo - TOL_MM || xMm > hi + TOL_MM) continue;
    const t =
      Math.abs(e.x - s.x) < 1
        ? 0.5
        : Math.max(0, Math.min(1, (xMm - s.x) / (e.x - s.x)));
    const y = s.y + t * (e.y - s.y);
    const score = Math.abs(((s.x + e.x) / 2) - xMm);
    if (score < bestScore) {
      bestScore = score;
      bestY = y;
    }
  }

  return bestY ?? 0;
}

function buildTrussChordPanels(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
  kind: "tc" | "bc",
): Array<TrussTcPanel | TrussBcPanel> {
  const segments = collectTrussSegments(elements);
  if (segments.length === 0 || grid.zCoordsMm.length < 2) {
    return [];
  }

  const xPositions = trussXLayout(segments, kind);
  if (xPositions.length < 2) {
    return [];
  }

  const out: Array<TrussTcPanel | TrussBcPanel> = [];

  for (let zBayIndex = 0; zBayIndex < grid.zCoordsMm.length - 1; zBayIndex += 1) {
    const z0Mm = grid.zCoordsMm[zBayIndex];
    const z1Mm = grid.zCoordsMm[zBayIndex + 1];
    const [zStart, zEnd] = zPanelGridRefs(z0Mm, z1Mm, grid);

    for (let xPanelIndex = 0; xPanelIndex < xPositions.length - 1; xPanelIndex += 1) {
      const x0Mm = xPositions[xPanelIndex];
      const x1Mm = xPositions[xPanelIndex + 1];
      const [xStart, xEnd] = xPanelGridRefs(x0Mm, x1Mm, grid);
      const xCenter = (x0Mm + x1Mm) / 2;
      const [xAxis] = xPanelGridRefs(xCenter, xCenter, grid);
      const chordLabel = kind === "tc" ? "TC truss" : "BC truss";

      if (kind === "tc") {
        out.push({
          kind: "truss_tc",
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
          elevation: "roof",
          label: `${chordLabel} · ${xStart} → ${xEnd} · Frame ${zStart} → ${zEnd}`,
        });
      } else {
        out.push({
          kind: "truss_bc",
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
          elevation: "eave",
          label: `${chordLabel} · ${xStart} → ${xEnd} · Frame ${zStart} → ${zEnd}`,
        });
      }
    }
  }

  return out;
}

export function buildTrussTcPanels(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): TrussTcPanel[] {
  if (!hasTrussSegments(elements)) return [];
  return buildTrussChordPanels(elements, grid, "tc") as TrussTcPanel[];
}

export function buildTrussBcPanels(
  elements: ProjectElementMm[],
  grid: StructuralGridState,
): TrussBcPanel[] {
  if (!hasTrussSegments(elements)) return [];
  return buildTrussChordPanels(elements, grid, "bc") as TrussBcPanel[];
}

export function trussPanelCornersMm(
  panel: TrussTcPanel | TrussBcPanel,
  segments: TrussSegment[],
): [
  TrussPanelCornerMm,
  TrussPanelCornerMm,
  TrussPanelCornerMm,
  TrussPanelCornerMm,
] {
  const kind = panel.kind === "truss_tc" ? "tc" : "bc";
  const y00 = yOnChordAtX(segments, kind, panel.z0Mm, panel.x0Mm);
  const y10 = yOnChordAtX(segments, kind, panel.z0Mm, panel.x1Mm);
  const y01 = yOnChordAtX(segments, kind, panel.z1Mm, panel.x0Mm);
  const y11 = yOnChordAtX(segments, kind, panel.z1Mm, panel.x1Mm);

  return [
    { x: panel.x0Mm, y: y00, z: panel.z0Mm },
    { x: panel.x1Mm, y: y10, z: panel.z0Mm },
    { x: panel.x0Mm, y: y01, z: panel.z1Mm },
    { x: panel.x1Mm, y: y11, z: panel.z1Mm },
  ];
}

import { isColumnElement } from "@/lib/column-member-scope";
import { memberEndpointsMm } from "@/lib/memberFrame";
import { gridLineNumber, type StructuralGridState } from "@/lib/structural-grid";
import type { ProjectElementMm } from "@/types/project";
import type { EnrichedSnapNode, SketchApplyScope } from "@/types/sketch";

export type BracingPlacement = {
  start: { x: number; y: number; z: number };
  end: { x: number; y: number; z: number };
};

export type TieBeamPlacement = {
  xAxis: string;
  zStart: string;
  zEnd: string;
  elevation: string;
};

const TOL_MM = 400;
/** Match backend `_ENDPOINT_ROUND_MM` for span deduplication. */
const SPAN_ROUND_MM = 1;

function roundMm(value: number): number {
  return Math.round(value / SPAN_ROUND_MM) * SPAN_ROUND_MM;
}

function spanKey(placement: BracingPlacement): string {
  const a = [
    roundMm(placement.start.x),
    roundMm(placement.start.y),
    roundMm(placement.start.z),
  ].join(",");
  const b = [
    roundMm(placement.end.x),
    roundMm(placement.end.y),
    roundMm(placement.end.z),
  ].join(",");
  return [a, b].sort().join("|");
}

function isSameSpan(a: BracingPlacement, b: BracingPlacement): boolean {
  return spanKey(a) === spanKey(b);
}

export function dedupePlacements(placements: BracingPlacement[]): BracingPlacement[] {
  const out: BracingPlacement[] = [];
  for (const p of placements) {
    if (!out.some((existing) => isSameSpan(existing, p))) {
      out.push(p);
    }
  }
  return out;
}

function parseColumnAxes(
  elementId: string,
): { xAxis: string; zAxis: string } | null {
  const m = elementId.match(/-col-([A-Z]+)-(.+)$/);
  if (!m) return null;
  const zAxis = m[2].replace(/p/g, "+").replace(/_/g, "/");
  return { xAxis: m[1], zAxis };
}

function bayPairsForScope(
  grid: StructuralGridState,
  scope: SketchApplyScope,
  rowBay?: { zStart: string; zEnd: string },
): Array<{ zStart: string; zEnd: string }> {
  const zLabels = grid.zCoordsMm.map((_, i) => gridLineNumber(i));
  const pairs: Array<{ zStart: string; zEnd: string }> = [];
  for (let i = 0; i < zLabels.length - 1; i += 1) {
    pairs.push({ zStart: zLabels[i], zEnd: zLabels[i + 1] });
  }
  if (scope === "all_bays") return pairs;
  if (scope === "row" && rowBay) {
    return pairs.filter(
      (p) => p.zStart === rowBay.zStart && p.zEnd === rowBay.zEnd,
    );
  }
  if (scope === "single" && rowBay) {
    return [rowBay];
  }
  return rowBay ? [rowBay] : pairs.slice(0, 1);
}

function inferBayFromNodes(
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
  grid: StructuralGridState,
): { zStart: string; zEnd: string } | null {
  const zLabels = grid.zCoordsMm.map((_, i) => gridLineNumber(i));
  const startZ = parseColumnAxes(start.elementId)?.zAxis;
  const endZ = parseColumnAxes(end.elementId)?.zAxis;
  if (!startZ || !endZ) return null;
  const si = zLabels.indexOf(startZ);
  const ei = zLabels.indexOf(endZ);
  if (si < 0 || ei < 0) return null;
  const lo = Math.min(si, ei);
  const hi = Math.max(si, ei);
  if (hi - lo !== 1) return null;
  return { zStart: zLabels[lo], zEnd: zLabels[hi] };
}

function isTrussChordElement(element: ProjectElementMm): boolean {
  const et = (element.element_type ?? "").toLowerCase();
  const id = element.id.toLowerCase();
  return et === "truss_chord" || id.includes("-truss-tc-") || id.includes("-truss-bc-");
}

function isTrussRoofBracing(
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
): boolean {
  const onTruss =
    isTrussChordElement({ id: start.elementId, element_type: start.elementType } as ProjectElementMm) ||
    isTrussChordElement({ id: end.elementId, element_type: end.elementType } as ProjectElementMm) ||
    /-truss-(tc|bc)/i.test(start.elementId) ||
    /-truss-(tc|bc)/i.test(end.elementId);
  const onColumn =
    start.elementType === "column" ||
    end.elementType === "column" ||
    /-col-/i.test(start.elementId) ||
    /-col-/i.test(end.elementId);
  if (onColumn && !onTruss) return false;
  const spansFrame = Math.abs(end.z - start.z) > 200;
  return onTruss && spansFrame;
}

const FRAME_Z_TOL_MM = 200;
const PANEL_X_TOL_MM = 350;

type Point3 = { x: number; y: number; z: number };

function trussSegments(
  elements: ProjectElementMm[],
): Array<{ start: Point3; end: Point3 }> {
  const out: Array<{ start: Point3; end: Point3 }> = [];
  for (const el of elements) {
    if (!isTrussChordElement(el)) continue;
    const ep = memberEndpointsMm(el);
    if (!ep) continue;
    out.push({
      start: { x: ep.start.x, y: ep.start.y, z: ep.start.z },
      end: { x: ep.end.x, y: ep.end.y, z: ep.end.z },
    });
  }
  return out;
}

function pointOnFrameAtX(
  segments: Array<{ start: Point3; end: Point3 }>,
  frameZ: number,
  xMm: number,
  referenceY?: number,
): Point3 | null {
  let best: Point3 | null = null;
  let bestScore = Infinity;

  for (const seg of segments) {
    for (const pt of [seg.start, seg.end]) {
      if (Math.abs(pt.z - frameZ) > FRAME_Z_TOL_MM) continue;
      const dx = Math.abs(pt.x - xMm);
      if (dx > PANEL_X_TOL_MM) continue;
      const score = dx + (referenceY !== undefined ? Math.abs(pt.y - referenceY) * 0.01 : 0);
      if (score < bestScore) {
        bestScore = score;
        best = pt;
      }
    }
    const { start: s, end: e } = seg;
    if (Math.abs(s.z - frameZ) > FRAME_Z_TOL_MM && Math.abs(e.z - frameZ) > FRAME_Z_TOL_MM) {
      continue;
    }
    const lo = Math.min(s.x, e.x);
    const hi = Math.max(s.x, e.x);
    if (xMm < lo - PANEL_X_TOL_MM || xMm > hi + PANEL_X_TOL_MM) continue;
    const t =
      Math.abs(e.x - s.x) < 1
        ? 0.5
        : Math.max(0, Math.min(1, (xMm - s.x) / (e.x - s.x)));
    const interp = {
      x: s.x + t * (e.x - s.x),
      y: s.y + t * (e.y - s.y),
      z: s.z + t * (e.z - s.z),
    };
    if (Math.abs(interp.z - frameZ) > FRAME_Z_TOL_MM) continue;
    const dx = Math.abs(interp.x - xMm);
    const score = dx + (referenceY !== undefined ? Math.abs(interp.y - referenceY) * 0.01 : 0);
    if (score < bestScore) {
      bestScore = score;
      best = interp;
    }
  }
  return best;
}

/** Roof X-brace legs between truss panel nodes on adjacent frames. */
export function findMatchingRoofXBraceLegs(
  elements: ProjectElementMm[],
  template: BracingPlacement,
  scope: SketchApplyScope,
  grid: StructuralGridState,
  startNode: EnrichedSnapNode,
  endNode: EnrichedSnapNode,
): BracingPlacement[] {
  if (scope === "single") return [template];

  const segments = trussSegments(elements);
  if (segments.length === 0) return [template];

  const zA = template.start.z;
  const zB = template.end.z;
  const xA = template.start.x;
  const xB = template.end.x;
  const yA = template.start.y;
  const yB = template.end.y;

  const zLabels = grid.zCoordsMm.map((_, i) => gridLineNumber(i));
  const rowBay = inferBayFromNodes(startNode, endNode, grid);
  const bays = bayPairsForScope(grid, scope, rowBay ?? undefined);

  const placements: BracingPlacement[] = [];

  for (const bay of bays) {
    const si = zLabels.indexOf(bay.zStart);
    const ei = zLabels.indexOf(bay.zEnd);
    if (si < 0 || ei < 0) continue;
    const zLo = grid.zCoordsMm[si];
    const zHi = grid.zCoordsMm[ei];

    const isSketchBay =
      rowBay &&
      bay.zStart === rowBay.zStart &&
      bay.zEnd === rowBay.zEnd;

    if (isSketchBay) {
      placements.push(template);
      continue;
    }

    const startOnLo = pointOnFrameAtX(segments, zLo, xA, yA);
    const endOnHi = pointOnFrameAtX(segments, zHi, xB, yB);
    if (!startOnLo || !endOnHi) continue;

    const candidate: BracingPlacement = {
      start: { x: startOnLo.x, y: startOnLo.y, z: startOnLo.z },
      end: { x: endOnHi.x, y: endOnHi.y, z: endOnHi.z },
    };
    if (!placements.some((p) => isSameSpan(p, candidate))) {
      placements.push(candidate);
    }
  }

  return placements.length > 0 ? dedupePlacements(placements) : [template];
}

export { isTrussRoofBracing };

/** Find bracing placements matching the template line geometry. */
export function findMatchingBracingPlacements(
  elements: ProjectElementMm[],
  template: BracingPlacement,
  scope: SketchApplyScope,
  grid: StructuralGridState,
  startNode: EnrichedSnapNode,
  endNode: EnrichedSnapNode,
): BracingPlacement[] {
  const span = Math.hypot(
    template.end.x - template.start.x,
    template.end.y - template.start.y,
    template.end.z - template.start.z,
  );
  const rowBay = inferBayFromNodes(startNode, endNode, grid);

  if (scope === "single") return [template];

  const placements: BracingPlacement[] = [];

  const columns = elements.filter(isColumnElement);
  const columnNodes: Array<{
    id: string;
    bottom: { x: number; y: number; z: number };
    top: { x: number; y: number; z: number };
  }> = [];

  for (const col of columns) {
    const ep = memberEndpointsMm(col);
    if (!ep) continue;
    columnNodes.push({
      id: col.id,
      bottom: { x: ep.start.x, y: ep.start.y, z: ep.start.z },
      top: { x: ep.end.x, y: ep.end.y, z: ep.end.z },
    });
  }

  const templateDy = template.end.y - template.start.y;

  for (let i = 0; i < columnNodes.length; i += 1) {
    for (let j = i + 1; j < columnNodes.length; j += 1) {
      const a = columnNodes[i];
      const b = columnNodes[j];
      const pairs: BracingPlacement[] = [
        { start: a.bottom, end: b.top },
        { start: b.bottom, end: a.top },
        { start: a.top, end: b.bottom },
        { start: b.top, end: a.bottom },
      ];
      for (const p of pairs) {
        const len = Math.hypot(
          p.end.x - p.start.x,
          p.end.y - p.start.y,
          p.end.z - p.start.z,
        );
        if (Math.abs(len - span) > TOL_MM) continue;
        const dy = p.end.y - p.start.y;
        if (Math.sign(dy) !== Math.sign(templateDy) && templateDy !== 0) continue;
        if (!placements.some((existing) => isSameSpan(existing, p))) {
          placements.push(p);
        }
      }
    }
  }

  let result = placements;
  if (scope === "row" && rowBay) {
    result = placements.filter(
      (p) => nodeInBay(p.start, rowBay, grid) || nodeInBay(p.end, rowBay, grid),
    );
  }
  if (result.length === 0) return [template];
  if (!result.some((p) => isSameSpan(p, template))) {
    result = [template, ...result];
  }
  return dedupePlacements(result);
}

function nodeInBay(
  pt: { x: number; z: number },
  bay: { zStart: string; zEnd: string },
  grid: StructuralGridState,
): boolean {
  const zLabels = grid.zCoordsMm.map((_, i) => gridLineNumber(i));
  const si = zLabels.indexOf(bay.zStart);
  const ei = zLabels.indexOf(bay.zEnd);
  if (si < 0 || ei < 0) return true;
  const zMin = grid.zCoordsMm[si];
  const zMax = grid.zCoordsMm[ei];
  return pt.z >= zMin - TOL_MM && pt.z <= zMax + TOL_MM;
}

function distance3d(
  a: { x: number; y: number; z: number },
  b: { x: number; y: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

/** Resolve tie-beam grid placements for scope expansion. */
export function findMatchingTieBeamPlacements(
  startNode: EnrichedSnapNode,
  endNode: EnrichedSnapNode,
  grid: StructuralGridState,
  scope: SketchApplyScope,
  elevation = "eave",
): TieBeamPlacement[] {
  const startAxes = parseColumnAxes(startNode.elementId);
  const endAxes = parseColumnAxes(endNode.elementId);
  if (!startAxes || !endAxes) return [];
  if (startAxes.xAxis !== endAxes.xAxis) return [];

  const rowBay = inferBayFromNodes(startNode, endNode, grid);
  const bays = bayPairsForScope(grid, scope, rowBay ?? undefined);
  const xAxis = startAxes.xAxis;

  return bays.map((bay) => ({
    xAxis,
    zStart: bay.zStart,
    zEnd: bay.zEnd,
    elevation,
  }));
}

/** Tie-beam segments at the sketched elevation (exact mm), expanded by scope. */
export function findMatchingTieBeamSegments(
  template: BracingPlacement,
  grid: StructuralGridState,
  scope: SketchApplyScope,
  startNode: EnrichedSnapNode,
  endNode: EnrichedSnapNode,
): BracingPlacement[] {
  if (scope === "single") return [template];

  const startAxes = parseColumnAxes(startNode.elementId);
  const endAxes = parseColumnAxes(endNode.elementId);
  if (!startAxes || !endAxes || startAxes.xAxis !== endAxes.xAxis) {
    return [template];
  }

  const zLabels = grid.zCoordsMm.map((_, i) => gridLineNumber(i));
  const rowBay = inferBayFromNodes(startNode, endNode, grid);
  const bays = bayPairsForScope(grid, scope, rowBay ?? undefined);
  const xMm = template.start.x;
  const placements: BracingPlacement[] = [];

  for (const bay of bays) {
    const si = zLabels.indexOf(bay.zStart);
    const ei = zLabels.indexOf(bay.zEnd);
    if (si < 0 || ei < 0) continue;
    const isSketchBay =
      rowBay &&
      bay.zStart === rowBay.zStart &&
      bay.zEnd === rowBay.zEnd;
    const candidate: BracingPlacement = isSketchBay
      ? template
      : {
          start: {
            x: xMm,
            y: template.start.y,
            z: grid.zCoordsMm[si],
          },
          end: {
            x: xMm,
            y: template.end.y,
            z: grid.zCoordsMm[ei],
          },
        };
    if (!placements.some((p) => isSameSpan(p, candidate))) {
      placements.push(candidate);
    }
  }

  return placements.length > 0 ? dedupePlacements(placements) : [template];
}

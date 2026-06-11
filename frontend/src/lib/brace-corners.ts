import { memberEndpointsMm } from "@/lib/memberFrame";
import type { ProjectElementMm } from "@/types/project";
import type { OperationProposal } from "@/types/structural-advise";
import type { EnrichedSnapNode } from "@/types/sketch";

export type Point3Mm = { x: number; y: number; z: number };
export type XBraceCorners = [Point3Mm, Point3Mm, Point3Mm, Point3Mm];

const SPAN_ROUND_MM = 1;

function dist(a: Point3Mm, b: Point3Mm): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

function roundMm(value: number): number {
  return Math.round(value / SPAN_ROUND_MM) * SPAN_ROUND_MM;
}

function roundPoint(pt: Point3Mm): Point3Mm {
  return { x: roundMm(pt.x), y: roundMm(pt.y), z: roundMm(pt.z) };
}

/** Order-independent span id — must match backend model_edit._span_key rounding. */
export function spanKeyMm(
  start: Point3Mm,
  end: Point3Mm,
): string {
  const a = roundPoint(start);
  const b = roundPoint(end);
  const sa = `${a.x},${a.y},${a.z}`;
  const sb = `${b.x},${b.y},${b.z}`;
  return sa < sb ? `${sa}|${sb}` : `${sb}|${sa}`;
}

function isColumn(element: ProjectElementMm): boolean {
  const et = (element.element_type ?? "").toLowerCase();
  return et === "column" || element.id.toLowerCase().includes("-col-");
}

function columnById(
  elements: ProjectElementMm[],
  elementId: string | undefined,
): ProjectElementMm | null {
  if (!elementId) return null;
  const el = elements.find((item) => item.id === elementId);
  return el && isColumn(el) ? el : null;
}

export function hasColumnHosts(
  elements: ProjectElementMm[],
  startElementId?: string,
  endElementId?: string,
): boolean {
  const colA = columnById(elements, startElementId);
  const colB = columnById(elements, endElementId);
  return Boolean(colA && colB && colA.id !== colB.id);
}

function columnBottomTop(
  element: ProjectElementMm,
): [Point3Mm, Point3Mm] | null {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;
  const low: Point3Mm = { x: ep.start.x, y: ep.start.y, z: ep.start.z };
  const high: Point3Mm = { x: ep.end.x, y: ep.end.y, z: ep.end.z };
  return low.y <= high.y ? [low, high] : [high, low];
}

function diagonalMatchScore(
  start: Point3Mm,
  end: Point3Mm,
  p: Point3Mm,
  q: Point3Mm,
): number {
  return Math.min(
    dist(start, p) + dist(end, q),
    dist(start, q) + dist(end, p),
  );
}

function inferWallXFromCoords(
  start: Point3Mm,
  end: Point3Mm,
): XBraceCorners | null {
  const dz = Math.abs(end.z - start.z);
  const dx = Math.abs(end.x - start.x);
  let c1: Point3Mm;
  let c2: Point3Mm;
  let c3: Point3Mm;
  let c4: Point3Mm;

  if (dz >= dx && dz > 200) {
    c1 = { x: start.x, y: start.y, z: start.z };
    c4 = { x: start.x, y: start.y, z: end.z };
    c2 = { x: end.x, y: end.y, z: start.z };
    c3 = { x: end.x, y: end.y, z: end.z };
  } else if (dx > dz && dx > 200) {
    c1 = { x: start.x, y: start.y, z: start.z };
    c2 = { x: end.x, y: start.y, z: start.z };
    c4 = { x: start.x, y: end.y, z: end.z };
    c3 = { x: end.x, y: end.y, z: end.z };
  } else {
    return null;
  }

  const diag1 = diagonalMatchScore(start, end, c1, c3);
  const diag2 = diagonalMatchScore(start, end, c2, c4);
  if (diag1 <= diag2) {
    return [c1, c3, c2, c4];
  }
  return [c2, c4, c1, c3];
}

/** Full wall-bay X corners (leg1 a→b, leg2 c→d) from column hosts when possible. */
export function inferWallXBraceCorners(
  start: Point3Mm,
  end: Point3Mm,
  elements: ProjectElementMm[],
  startElementId?: string,
  endElementId?: string,
): XBraceCorners | null {
  const colA = columnById(elements, startElementId);
  const colB = columnById(elements, endElementId);
  if (!colA || !colB || colA.id === colB.id) {
    return inferWallXFromCoords(start, end);
  }

  const aEnds = columnBottomTop(colA);
  const bEnds = columnBottomTop(colB);
  if (!aEnds || !bEnds) {
    return inferWallXFromCoords(start, end);
  }

  const [aBot, aTop] = aEnds;
  const [bBot, bTop] = bEnds;
  const diag1 = diagonalMatchScore(start, end, aBot, bTop);
  const diag2 = diagonalMatchScore(start, end, aTop, bBot);
  if (diag1 <= diag2) {
    return [aBot, bTop, aTop, bBot];
  }
  return [aTop, bBot, aBot, bTop];
}

export function isValidXBraceCorners(
  corners: Point3Mm[] | null | undefined,
): corners is XBraceCorners {
  return Array.isArray(corners) && corners.length === 4;
}

export function xBraceLegsAreDistinct(corners: XBraceCorners): boolean {
  const [a, b, c, d] = corners;
  return spanKeyMm(a, b) !== spanKeyMm(c, d);
}

/** Prefer column corner geometry over advise/API corners when snap hosts are columns. */
export function resolveXBraceCorners(
  op: OperationProposal | undefined,
  locked: { start: EnrichedSnapNode; end: EnrichedSnapNode },
  elements: ProjectElementMm[],
): XBraceCorners | null {
  const start = { x: locked.start.x, y: locked.start.y, z: locked.start.z };
  const end = { x: locked.end.x, y: locked.end.y, z: locked.end.z };

  if (hasColumnHosts(elements, locked.start.elementId, locked.end.elementId)) {
    const fromColumns = inferWallXBraceCorners(
      start,
      end,
      elements,
      locked.start.elementId,
      locked.end.elementId,
    );
    if (fromColumns && xBraceLegsAreDistinct(fromColumns)) {
      return fromColumns;
    }
  }

  const fromOp = op?.x_corners_mm;
  if (fromOp && isValidXBraceCorners(fromOp) && xBraceLegsAreDistinct(fromOp)) {
    return [fromOp[0], fromOp[1], fromOp[2], fromOp[3]];
  }

  const fallback = inferWallXBraceCorners(
    start,
    end,
    elements,
    locked.start.elementId,
    locked.end.elementId,
  );
  if (fallback && xBraceLegsAreDistinct(fallback)) {
    return fallback;
  }
  return null;
}

function isBraceElement(element: ProjectElementMm): boolean {
  const et = (element.element_type ?? "").toLowerCase();
  return et === "bracing" || element.id.toLowerCase().includes("brace");
}

function elementSpanKey(element: ProjectElementMm): string | null {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;
  return spanKeyMm(
    { x: ep.start.x, y: ep.start.y, z: ep.start.z },
    { x: ep.end.x, y: ep.end.y, z: ep.end.z },
  );
}

/** Count how many distinct X legs exist in the model at the target spans. */
export function verifyXBraceLegsInModel(
  elements: ProjectElementMm[],
  corners: XBraceCorners,
): { legCount: number; legIds: string[] } {
  const [a, b, c, d] = corners;
  const leg1 = spanKeyMm(a, b);
  const leg2 = spanKeyMm(c, d);
  const idsBySpan = new Map<string, string[]>();

  for (const element of elements) {
    if (!isBraceElement(element)) continue;
    const sk = elementSpanKey(element);
    if (!sk || (sk !== leg1 && sk !== leg2)) continue;
    const list = idsBySpan.get(sk) ?? [];
    list.push(element.id);
    idsBySpan.set(sk, list);
  }

  const legIds = [...idsBySpan.values()].flat();
  return { legCount: idsBySpan.size, legIds };
}

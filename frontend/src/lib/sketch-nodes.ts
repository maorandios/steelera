import * as THREE from "three";

import { memberEndpointsMm } from "@/lib/memberFrame";
import type { StructuralGridState } from "@/lib/structural-grid";
import type { ProjectElementMm } from "@/types/project";
import type { EnrichedSnapNode } from "@/types/sketch";

const MIN_MEMBER_SPAN_MM = 150;
const MIN_NODE_SEP_MM = 40;
const BAY_BREAK_TOL_MM = 30;

/** Snap positions along each member: start, 30 %, 50 %, 70 %, end. */
const SNAP_FRACTIONS = [0, 0.3, 0.5, 0.7, 1] as const;

const SKETCH_EXCLUDED_TYPES = new Set([
  "purlin",
  "wall_girt",
  "girt",
  "truss_web",
  "sag_rod",
  "bracing",
]);

const SKETCHABLE_TYPES = new Set([
  "column",
  "rafter",
  "tie_beam",
  "truss_chord",
  "beam",
]);

function vec3FromCoords(coords: unknown): THREE.Vector3 | null {
  if (!Array.isArray(coords) || coords.length < 3) return null;
  const [x, y, z] = coords;
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
    return null;
  }
  return new THREE.Vector3(x, y, z);
}

function isTieBeamLike(element: ProjectElementMm): boolean {
  const type = (element.element_type ?? "").toLowerCase();
  if (type === "tie_beam") return true;
  const id = element.id.toLowerCase();
  return (
    id.includes("-tie-") ||
    id.includes("-bctie-") ||
    id.includes("bctie") ||
    id.includes("-tie-ridge")
  );
}

/** Resolve structural kind even when element_type is missing on older payloads. */
export function resolveSketchElementType(element: ProjectElementMm): string | null {
  if (isTieBeamLike(element)) return "tie_beam";

  const type = (element.element_type ?? "").toLowerCase();
  if (type && SKETCH_EXCLUDED_TYPES.has(type)) return null;
  if (type && SKETCHABLE_TYPES.has(type)) return type;

  const id = element.id.toLowerCase();
  if (id.includes("-truss-tc-") || id.includes("-truss-bc-")) return "truss_chord";
  if (id.includes("-col-")) return "column";
  if (id.includes("-rafter-")) return "rafter";
  if (id.includes("-beam-")) return "beam";

  return null;
}

/** Endpoints in mm — prefers connection nodes, falls back to axis extrusion. */
export function sketchMemberEndpointsMm(
  element: ProjectElementMm,
): { start: THREE.Vector3; end: THREE.Vector3 } | null {
  const ep = memberEndpointsMm(element);
  if (ep) {
    return { start: ep.start.clone(), end: ep.end.clone() };
  }

  const nodes = element.nodes;
  if (nodes) {
    const start = vec3FromCoords(nodes.start ?? nodes.bottom);
    const end = vec3FromCoords(nodes.end ?? nodes.top);
    if (start && end) return { start, end };
  }

  const pos = element.position_mm;
  const len = element.length_mm;
  if (!Number.isFinite(len) || len < MIN_MEMBER_SPAN_MM) return null;

  const { x, y, z } = pos;
  const axis = element.axis ?? "y";
  if (axis === "x") {
    return {
      start: new THREE.Vector3(x, y, z),
      end: new THREE.Vector3(x + len, y, z),
    };
  }
  if (axis === "z") {
    return {
      start: new THREE.Vector3(x, y, z),
      end: new THREE.Vector3(x, y, z + len),
    };
  }
  return {
    start: new THREE.Vector3(x, y, z),
    end: new THREE.Vector3(x, y + len, z),
  };
}

export function isSketchableElement(element: ProjectElementMm): boolean {
  if (!resolveSketchElementType(element)) return false;
  return sketchMemberEndpointsMm(element) !== null;
}

function lerpPoint(
  start: THREE.Vector3,
  end: THREE.Vector3,
  t: number,
): { x: number; y: number; z: number } {
  const pt = start.clone().lerp(end, t);
  return { x: pt.x, y: pt.y, z: pt.z };
}

function dominantAxis(start: THREE.Vector3, end: THREE.Vector3): "x" | "y" | "z" {
  const d = end.clone().sub(start);
  const ax = Math.abs(d.x);
  const ay = Math.abs(d.y);
  const az = Math.abs(d.z);
  if (ax >= ay && ax >= az) return "x";
  if (az >= ax && az >= ay) return "z";
  return "y";
}

function gridCoordsForAxis(
  grid: StructuralGridState,
  axis: "x" | "y" | "z",
): number[] {
  if (axis === "x") return grid.xCoordsMm;
  if (axis === "z") return grid.zCoordsMm;
  return [];
}

/** Split a member into bay-length segments using structural grid frame lines. */
export function splitMemberIntoBaySegments(
  start: THREE.Vector3,
  end: THREE.Vector3,
  gridCoordsMm: number[],
): Array<{ start: THREE.Vector3; end: THREE.Vector3 }> {
  if (gridCoordsMm.length < 2) {
    return [{ start: start.clone(), end: end.clone() }];
  }

  const axis = dominantAxis(start, end);
  const a0 = start[axis];
  const a1 = end[axis];
  if (Math.abs(a1 - a0) < MIN_MEMBER_SPAN_MM) {
    return [{ start: start.clone(), end: end.clone() }];
  }

  const minA = Math.min(a0, a1);
  const maxA = Math.max(a0, a1);

  const interiorBreaks = gridCoordsMm.filter(
    (c) => c > minA + BAY_BREAK_TOL_MM && c < maxA - BAY_BREAK_TOL_MM,
  );

  const knots: number[] = [a0];
  for (const c of interiorBreaks.sort((a, b) => a - b)) {
    const last = knots[knots.length - 1];
    if (Math.abs(c - last) > BAY_BREAK_TOL_MM) knots.push(c);
  }
  if (Math.abs(maxA - knots[knots.length - 1]) > BAY_BREAK_TOL_MM) {
    knots.push(a1);
  } else {
    knots[knots.length - 1] = a1;
  }

  const segments: Array<{ start: THREE.Vector3; end: THREE.Vector3 }> = [];
  for (let i = 0; i < knots.length - 1; i++) {
    const t0 = (knots[i] - a0) / (a1 - a0);
    const t1 = (knots[i + 1] - a0) / (a1 - a0);
    segments.push({
      start: start.clone().lerp(end, t0),
      end: start.clone().lerp(end, t1),
    });
  }

  return segments.length > 0 ? segments : [{ start: start.clone(), end: end.clone() }];
}

/** Snap fractions for one member — always 0 / 30 / 50 / 70 / 100 % when span allows. */
export function snapFractionsAlongMember(spanMm: number): number[] {
  if (spanMm < MIN_MEMBER_SPAN_MM) return [];

  const picked: number[] = [];
  for (const t of SNAP_FRACTIONS) {
    const posMm = t * spanMm;
    const tooClose = picked.some(
      (existing) => Math.abs(existing * spanMm - posMm) < MIN_NODE_SEP_MM,
    );
    if (!tooClose) picked.push(t);
  }
  return picked;
}

function pushSnapNodesForSegment(
  nodes: EnrichedSnapNode[],
  element: ProjectElementMm,
  kind: string,
  segStart: THREE.Vector3,
  segEnd: THREE.Vector3,
  segKey: string,
): void {
  const span = segStart.distanceTo(segEnd);
  for (const t of snapFractionsAlongMember(span)) {
    const pt = lerpPoint(segStart, segEnd, t);
    nodes.push({
      id: `${element.id}:${segKey}:t${Math.round(t * 1000)}`,
      ...pt,
      tier: "primary",
      elementId: element.id,
      elementType: kind,
      paramAlongMember: t,
    });
  }
}

/** Build snap nodes along sketchable members. */
export function buildSketchSnapNodes(
  elements: ProjectElementMm[],
  grid?: StructuralGridState,
): EnrichedSnapNode[] {
  const nodes: EnrichedSnapNode[] = [];

  for (const element of elements) {
    const kind = resolveSketchElementType(element);
    if (!kind) continue;

    const ep = sketchMemberEndpointsMm(element);
    if (!ep) continue;

    const fullSpan = ep.start.distanceTo(ep.end);
    if (fullSpan < MIN_MEMBER_SPAN_MM) continue;

    if (kind === "tie_beam" && grid) {
      const axis = dominantAxis(ep.start, ep.end);
      const gridCoords = gridCoordsForAxis(grid, axis);
      const segments = splitMemberIntoBaySegments(ep.start, ep.end, gridCoords);
      segments.forEach((seg, bayIdx) => {
        pushSnapNodesForSegment(nodes, element, kind, seg.start, seg.end, `bay${bayIdx}`);
      });
      continue;
    }

    pushSnapNodesForSegment(nodes, element, kind, ep.start, ep.end, "full");
  }

  return nodes;
}

export function findSketchNodeById(
  nodes: EnrichedSnapNode[],
  id: string,
): EnrichedSnapNode | null {
  return nodes.find((n) => n.id === id) ?? null;
}

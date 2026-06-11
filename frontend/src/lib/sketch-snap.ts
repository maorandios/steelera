import type { EnrichedSnapNode } from "@/types/sketch";

/** World-space magnetic snap radius (mm) — tuned for touch targets. */
export const SKETCH_SNAP_RADIUS_MM = 450;

/** Screen-space snap radius (px) — used when pointer raycast position is approximate. */
export const SKETCH_SNAP_RADIUS_PX = 36;

export function distance3dMm(
  a: { x: number; y: number; z: number },
  b: { x: number; y: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

export function findMagneticSnapNode(
  pointerWorldMm: { x: number; y: number; z: number },
  nodes: EnrichedSnapNode[],
  excludeId: string | null,
  radiusMm = SKETCH_SNAP_RADIUS_MM,
): EnrichedSnapNode | null {
  let best: EnrichedSnapNode | null = null;
  let bestDist = radiusMm;
  for (const node of nodes) {
    if (node.id === excludeId) continue;
    const d = distance3dMm(pointerWorldMm, node);
    if (d < bestDist) {
      best = node;
      bestDist = d;
    }
  }
  return best;
}

/**
 * Project nodes to screen pixels and pick the nearest within radius.
 * Plug in refined raycast math later; this stub uses simple orthographic projection.
 */
export function findMagneticSnapNodeScreen(
  clientX: number,
  clientY: number,
  canvasRect: DOMRect,
  nodes: EnrichedSnapNode[],
  excludeId: string | null,
  projectToScreen: (node: EnrichedSnapNode) => { x: number; y: number } | null,
  radiusPx = SKETCH_SNAP_RADIUS_PX,
): EnrichedSnapNode | null {
  const px = clientX - canvasRect.left;
  const py = clientY - canvasRect.top;
  let best: EnrichedSnapNode | null = null;
  let bestDist = radiusPx;
  for (const node of nodes) {
    if (node.id === excludeId) continue;
    const screen = projectToScreen(node);
    if (!screen) continue;
    const d = Math.hypot(screen.x - px, screen.y - py);
    if (d < bestDist) {
      best = node;
      bestDist = d;
    }
  }
  return best;
}

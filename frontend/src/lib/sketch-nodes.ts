import { memberEndpointsMm } from "@/lib/memberFrame";
import type { ProjectElementMm } from "@/types/project";
import type { EnrichedSnapNode } from "@/types/sketch";

const SECONDARY_FRACTIONS = [0.25, 0.33, 0.5, 0.67, 0.75];
const MERGE_TOLERANCE_MM = 150;

function distance3d(
  a: { x: number; y: number; z: number },
  b: { x: number; y: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

function mergeKey(x: number, y: number, z: number): string {
  const s = MERGE_TOLERANCE_MM;
  return `${Math.round(x / s)},${Math.round(y / s)},${Math.round(z / s)}`;
}

function isSketchableElement(element: ProjectElementMm): boolean {
  const type = (element.element_type ?? "").toLowerCase();
  if (type === "column" || type === "rafter" || type === "tie_beam") return true;
  if (type === "bracing" || type === "truss_chord" || type === "beam") return true;
  return Boolean(memberEndpointsMm(element));
}

function lerpPoint(
  start: { x: number; y: number; z: number },
  end: { x: number; y: number; z: number },
  t: number,
): { x: number; y: number; z: number } {
  return {
    x: start.x + (end.x - start.x) * t,
    y: start.y + (end.y - start.y) * t,
    z: start.z + (end.z - start.z) * t,
  };
}

function pushNode(
  bucket: Map<string, EnrichedSnapNode>,
  node: EnrichedSnapNode,
): void {
  const key = mergeKey(node.x, node.y, node.z);
  const existing = bucket.get(key);
  if (!existing) {
    bucket.set(key, node);
    return;
  }
  if (node.tier === "primary" && existing.tier === "secondary") {
    bucket.set(key, node);
  }
}

/** Build primary + secondary snap nodes from structural members. */
export function buildSketchSnapNodes(
  elements: ProjectElementMm[],
): EnrichedSnapNode[] {
  const bucket = new Map<string, EnrichedSnapNode>();

  for (const element of elements) {
    if (!isSketchableElement(element)) continue;
    const ep = memberEndpointsMm(element);
    if (!ep) continue;

    const elementType = element.element_type ?? "member";
    const start = { x: ep.start.x, y: ep.start.y, z: ep.start.z };
    const end = { x: ep.end.x, y: ep.end.y, z: ep.end.z };
    const span = distance3d(start, end);
    if (span < 200) continue;

    pushNode(bucket, {
      id: `${element.id}:start`,
      ...start,
      tier: "primary",
      elementId: element.id,
      elementType,
      paramAlongMember: 0,
    });
    pushNode(bucket, {
      id: `${element.id}:end`,
      ...end,
      tier: "primary",
      elementId: element.id,
      elementType,
      paramAlongMember: 1,
    });

    for (const t of SECONDARY_FRACTIONS) {
      const pt = lerpPoint(start, end, t);
      pushNode(bucket, {
        id: `${element.id}:t${Math.round(t * 100)}`,
        ...pt,
        tier: "secondary",
        elementId: element.id,
        elementType,
        paramAlongMember: t,
      });
    }
  }

  return [...bucket.values()];
}

export function findSketchNodeById(
  nodes: EnrichedSnapNode[],
  id: string,
): EnrichedSnapNode | null {
  return nodes.find((n) => n.id === id) ?? null;
}

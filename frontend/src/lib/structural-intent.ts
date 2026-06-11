import { isColumnElement } from "@/lib/column-member-scope";
import type { ProjectElementMm } from "@/types/project";
import type {
  EnrichedSnapNode,
  StructuralIntentKind,
  StructuralIntentResult,
} from "@/types/sketch";

const HORIZONTAL_Y_TOL_MM = 250;
const LOW_EAVE_Y_MM = 2000;
const HIGH_ROOF_Y_MM = 3500;

export function classifyAngle(
  dx: number,
  dy: number,
  dz: number,
): "horizontal" | "vertical" | "diagonal" {
  const horizLen = Math.hypot(dx, dz);
  const vertLen = Math.abs(dy);
  if (horizLen < 100 && vertLen > 300) return "vertical";
  if (vertLen < HORIZONTAL_Y_TOL_MM && horizLen > 300) return "horizontal";
  return "diagonal";
}

function elementForNode(
  elements: ProjectElementMm[],
  node: EnrichedSnapNode,
): ProjectElementMm | null {
  return elements.find((e) => e.id === node.elementId) ?? null;
}

function isLowNode(node: EnrichedSnapNode): boolean {
  return node.y < LOW_EAVE_Y_MM;
}

function isHighNode(node: EnrichedSnapNode): boolean {
  return node.y > HIGH_ROOF_Y_MM;
}

/** Mock AI intent recognition from a locked sketch line. */
export function recognizeStructuralIntent(
  start: EnrichedSnapNode,
  end: EnrichedSnapNode,
  elements: ProjectElementMm[],
): StructuralIntentResult {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = end.z - start.z;
  const spanMm = Math.hypot(dx, dy, dz);
  const angleClass = classifyAngle(dx, dy, dz);

  const startEl = elementForNode(elements, start);
  const endEl = elementForNode(elements, end);

  const base = {
    angleClass,
    spanMm,
    start: {
      elementType: start.elementType,
      z: start.z,
      elementId: start.elementId,
    },
    end: {
      elementType: end.elementType,
      z: end.z,
      elementId: end.elementId,
    },
  };

  if (
    angleClass === "horizontal" &&
    isColumnElement(startEl) &&
    isColumnElement(endEl) &&
    isLowNode(start) &&
    isLowNode(end)
  ) {
    return {
      ...base,
      kind: "tie_beam",
      label: "Tie Beam",
      confidence: 0.88,
    };
  }

  if (angleClass === "diagonal") {
    const low = isLowNode(start) || isLowNode(end);
    const joint =
      start.paramAlongMember === 0 ||
      start.paramAlongMember === 1 ||
      end.paramAlongMember === 0 ||
      end.paramAlongMember === 1;
    const truss =
      /-truss-(tc|bc|web)/i.test(start.elementId) ||
      /-truss-(tc|bc|web)/i.test(end.elementId) ||
      start.elementType === "truss_chord" ||
      end.elementType === "truss_chord";
    const onColumn =
      isColumnElement(startEl) || isColumnElement(endEl);
    const spansBay =
      Math.abs(end.z - start.z) > 500 || Math.abs(end.x - start.x) > 500;
    if ((low && joint) || truss || (onColumn && spansBay) || (joint && spansBay)) {
      return {
        ...base,
        kind: "bracing",
        label: truss ? "Roof Bracing" : onColumn ? "Wall Bracing" : "Bracing",
        confidence: truss ? 0.85 : 0.82,
      };
    }
  }

  if (
    angleClass === "horizontal" &&
    (isHighNode(start) || isHighNode(end))
  ) {
    return {
      ...base,
      kind: "purlin",
      label: "Purlin",
      confidence: 0.76,
    };
  }

  if (angleClass === "horizontal") {
    return {
      ...base,
      kind: "beam",
      label: "Beam",
      confidence: 0.65,
    };
  }

  if (angleClass === "vertical") {
    return {
      ...base,
      kind: "beam",
      label: "Vertical Member",
      confidence: 0.5,
    };
  }

  return {
    ...base,
    kind: "unknown",
    label: "Structural Member",
    confidence: 0.4,
  };
}

export function intentLabel(kind: StructuralIntentKind): string {
  const map: Record<StructuralIntentKind, string> = {
    tie_beam: "Tie Beam",
    bracing: "Bracing",
    purlin: "Purlin",
    beam: "Beam",
    unknown: "Structural Member",
  };
  return map[kind];
}

/** Span-rule profile recommendations from catalog families. */
export function recommendProfiles(
  spanMm: number,
  kind: StructuralIntentKind,
): string[] {
  if (kind === "tie_beam" || kind === "beam") {
    if (spanMm < 5000) return ["IPE 200", "HEB 160", "Custom"];
    if (spanMm < 8000) return ["IPE 240", "HEA 200", "Custom"];
    return ["IPE 300", "HEB 200", "Custom"];
  }
  if (kind === "bracing") {
    return ["L70x70x7", "L80x80x8", "Custom"];
  }
  if (kind === "purlin") {
    if (spanMm < 6000) return ["Z200x75x2.0", "C200x75x2.0", "Custom"];
    return ["Z250x90x2.5", "C250x90x2.5", "Custom"];
  }
  return ["IPE 200", "HEB 160", "Custom"];
}

export function normalizeProfile(profile: string): string {
  return profile.replace(/\s+/g, "").toUpperCase();
}

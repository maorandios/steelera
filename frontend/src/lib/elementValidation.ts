import type { ProjectElementMm } from "@/types/project";
import { geometryExtentsM, memberLengthM } from "@/lib/coordinates";
import { hasNodeDrivenFrame, memberNodeFrame } from "@/lib/memberFrame";

const MIN_LENGTH_M = 1e-6;
const MIN_SECTION_M = 1e-6;

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isValidCoordTriple(
  coords: unknown,
): coords is [number, number, number] {
  return (
    Array.isArray(coords) &&
    coords.length >= 3 &&
    isFiniteNumber(coords[0]) &&
    isFiniteNumber(coords[1]) &&
    isFiniteNumber(coords[2])
  );
}

function hasValidNodeEndpoints(element: ProjectElementMm): boolean {
  const nodes = element.nodes;
  if (!nodes) return false;
  if (nodes.start && nodes.end) {
    return isValidCoordTriple(nodes.start) && isValidCoordTriple(nodes.end);
  }
  if (nodes.bottom && nodes.top) {
    return isValidCoordTriple(nodes.bottom) && isValidCoordTriple(nodes.top);
  }
  return false;
}

function isValidQuaternion(q: [number, number, number, number]): boolean {
  if (!q.every(isFiniteNumber)) return false;
  const len = Math.hypot(q[0], q[1], q[2], q[3]);
  return len > 1e-6 && Number.isFinite(len);
}

/**
 * Returns false for elements with missing/NaN geometry that would break R3F matrices.
 */
export function isElementRenderable(element: ProjectElementMm): boolean {
  if (!element?.id) return false;

  const pos = element.position_mm;
  if (
    !pos ||
    !isFiniteNumber(pos.x) ||
    !isFiniteNumber(pos.y) ||
    !isFiniteNumber(pos.z)
  ) {
    if (!hasValidNodeEndpoints(element)) return false;
  }

  const { length, height, width } = geometryExtentsM(element);
  if (!isFiniteNumber(length) || length < MIN_LENGTH_M) return false;
  if (!isFiniteNumber(height) || height < MIN_SECTION_M) return false;
  if (!isFiniteNumber(width) || width < MIN_SECTION_M) return false;

  if (!isFiniteNumber(memberLengthM(element)) || memberLengthM(element) < MIN_LENGTH_M) {
    return false;
  }

  if (hasNodeDrivenFrame(element)) {
    if (!hasValidNodeEndpoints(element)) return false;
    const frame = memberNodeFrame(element);
    if (!frame) return false;
    if (!frame.centerM.every(isFiniteNumber)) return false;
    if (!frame.alignOffsetM.every(isFiniteNumber)) return false;
    if (!isFiniteNumber(frame.lengthM) || frame.lengthM < MIN_LENGTH_M) return false;
    if (!isValidQuaternion(frame.quaternion)) return false;
  }

  const euler = element.rotation_euler_deg;
  if (euler) {
    for (const component of euler) {
      if (!isFiniteNumber(component)) return false;
    }
  }

  return true;
}

export function filterRenderableElements(
  elements: ProjectElementMm[],
): ProjectElementMm[] {
  return elements.filter(isElementRenderable);
}

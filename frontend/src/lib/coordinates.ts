import type { ElementAlignment, ExtrusionAxis, ProjectElementMm } from "@/types/project";
import { memberAxisRotation } from "@/lib/iSectionShape";

const MM_TO_M = 0.001;

/**
 * Structural axis origin in world meters.
 * Prefer explicit connection nodes when present (backend source of truth).
 */
export function structuralAxisOriginM(
  element: ProjectElementMm,
): [number, number, number] {
  const axis = element.axis ?? "y";
  const nodes = element.nodes;

  if (axis === "y" && nodes?.bottom) {
    return [nodes.bottom[0] * MM_TO_M, nodes.bottom[1] * MM_TO_M, nodes.bottom[2] * MM_TO_M];
  }
  if ((axis === "x" || axis === "z") && nodes?.start) {
    return [nodes.start[0] * MM_TO_M, nodes.start[1] * MM_TO_M, nodes.start[2] * MM_TO_M];
  }

  return [
    element.position_mm.x * MM_TO_M,
    element.position_mm.y * MM_TO_M,
    element.position_mm.z * MM_TO_M,
  ];
}

export function backendSizeM(element: ProjectElementMm): [number, number, number] {
  return [
    element.size_mm.x * MM_TO_M,
    element.size_mm.y * MM_TO_M,
    element.size_mm.z * MM_TO_M,
  ];
}

export function memberLengthM(element: ProjectElementMm): number {
  return element.length_mm * MM_TO_M;
}

export function crossSectionDimensionsM(element: ProjectElementMm): {
  height: number;
  width: number;
} {
  if (element.section_mm) {
    return {
      height: element.section_mm.h * MM_TO_M,
      width: element.section_mm.b * MM_TO_M,
    };
  }

  const axis = (element.axis ?? "y") as ExtrusionAxis;
  const [sx, sy, sz] = backendSizeM(element);
  if (axis === "x") return { height: sy, width: sz };
  if (axis === "y") return { height: sz, width: sx };
  return { height: sy, width: sx };
}

export function geometryExtentsM(element: ProjectElementMm): {
  length: number;
  height: number;
  width: number;
} {
  const { height, width } = crossSectionDimensionsM(element);
  return { length: memberLengthM(element), height, width };
}

/** User rotation around member-local +X (length axis), in radians. */
export function elementRotationRad(element: ProjectElementMm): number {
  return ((element.rotation ?? 0) * Math.PI) / 180;
}

/**
 * Alignment offset in member-local space (+Y is cross-section height).
 * Applied to inner mesh only, inside the rotated outer group.
 */
export function meshAlignmentOffsetLocal(
  element: ProjectElementMm,
): [number, number, number] {
  const { height } = crossSectionDimensionsM(element);
  const alignment: ElementAlignment = element.alignment ?? "center";

  switch (alignment) {
    case "bottom":
      return [0, height * 0.5, 0];
    case "top":
      return [0, -height * 0.5, 0];
    default:
      return [0, 0, 0];
  }
}

export function memberAxisRotationEuler(element: ProjectElementMm): [number, number, number] {
  return memberAxisRotation((element.axis ?? "y") as ExtrusionAxis);
}

type Vec3 = [number, number, number];

function rotateX([x, y, z]: Vec3, angle: number): Vec3 {
  if (angle === 0) return [x, y, z];
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return [x, y * c - z * s, y * s + z * c];
}

function applyEuler([x, y, z]: Vec3, [ex, ey, ez]: Vec3): Vec3 {
  let v: Vec3 = [x, y, z];
  if (ex !== 0) v = rotateX(v, ex);
  if (ey !== 0) {
    const c = Math.cos(ey);
    const s = Math.sin(ey);
    v = [v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c];
  }
  if (ez !== 0) {
    const c = Math.cos(ez);
    const s = Math.sin(ez);
    v = [v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2]];
  }
  return v;
}

/** Transform member-local point to world (includes alignment when provided). */
export function memberLocalToWorld(
  element: ProjectElementMm,
  local: Vec3,
  includeAlignment: boolean,
): Vec3 {
  const origin = structuralAxisOriginM(element);
  const align = includeAlignment ? meshAlignmentOffsetLocal(element) : [0, 0, 0];
  const userRot = elementRotationRad(element);
  const axisRot = memberAxisRotationEuler(element);

  const aligned: Vec3 = [
    local[0] + align[0],
    local[1] + align[1],
    local[2] + align[2],
  ];
  const userRotated = rotateX(aligned, userRot);
  const world = applyEuler(userRotated, axisRot);
  return [origin[0] + world[0], origin[1] + world[1], origin[2] + world[2]];
}

function boundsFromElements(
  projectElements: ProjectElementMm[],
  includeAlignment: boolean,
) {
  if (projectElements.length === 0) {
    return {
      center: [0, 2, 0] as [number, number, number],
      size: 20,
    };
  }

  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  for (const el of projectElements) {
    const { length, height, width } = geometryExtentsM(el);

    const localCorners: Vec3[] = [
      [0, -height * 0.5, -width * 0.5],
      [length, -height * 0.5, -width * 0.5],
      [0, height * 0.5, -width * 0.5],
      [0, -height * 0.5, width * 0.5],
      [length, height * 0.5, -width * 0.5],
      [length, -height * 0.5, width * 0.5],
      [0, height * 0.5, width * 0.5],
      [length, height * 0.5, width * 0.5],
    ];

    for (const corner of localCorners) {
      const [px, py, pz] = memberLocalToWorld(el, corner, includeAlignment);
      minX = Math.min(minX, px);
      maxX = Math.max(maxX, px);
      minY = Math.min(minY, py);
      maxY = Math.max(maxY, py);
      minZ = Math.min(minZ, pz);
      maxZ = Math.max(maxZ, pz);
    }
  }

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const cz = (minZ + maxZ) / 2;
  const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 5);

  return {
    center: [cx, cy, cz] as [number, number, number],
    size: span,
  };
}

/**
 * Camera / grid framing — based on structural axis geometry only.
 * Alignment shifts the mesh, NOT the viewport or ground grid.
 */
export function sceneStructuralBounds(projectElements: ProjectElementMm[]) {
  return boundsFromElements(projectElements, false);
}

/** Full mesh bounds including alignment offsets. */
export function sceneBounds(projectElements: ProjectElementMm[]) {
  return boundsFromElements(projectElements, true);
}

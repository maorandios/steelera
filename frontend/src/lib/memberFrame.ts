import * as THREE from "three";

import type { ElementAlignment, ProjectElementMm } from "@/types/project";

const MM_TO_M = 0.001;
const DEG_TO_RAD = Math.PI / 180;

const LOCAL_LENGTH_AXIS = new THREE.Vector3(1, 0, 0);

export type MemberEndpointsMm = {
  start: THREE.Vector3;
  end: THREE.Vector3;
};

function crossSectionDimensionsM(element: ProjectElementMm): {
  height: number;
  width: number;
} {
  if (element.section_mm) {
    return {
      height: element.section_mm.h * MM_TO_M,
      width: element.section_mm.b * MM_TO_M,
    };
  }
  const axis = element.axis ?? "y";
  const sx = element.size_mm.x * MM_TO_M;
  const sy = element.size_mm.y * MM_TO_M;
  const sz = element.size_mm.z * MM_TO_M;
  if (axis === "x") return { height: sy, width: sz };
  if (axis === "y") return { height: sz, width: sx };
  return { height: sy, width: sx };
}

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

function isFiniteCoord(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function vec3FromNodes(coords: unknown): THREE.Vector3 | null {
  if (!Array.isArray(coords) || coords.length < 3) return null;
  const [x, y, z] = coords;
  if (!isFiniteCoord(x) || !isFiniteCoord(y) || !isFiniteCoord(z)) {
    return null;
  }
  return new THREE.Vector3(x, y, z);
}

/** Read structural connection nodes (mm). */
export function memberEndpointsMm(
  element: ProjectElementMm,
): MemberEndpointsMm | null {
  const nodes = element.nodes;
  if (!nodes) return null;

  if (nodes.start && nodes.end) {
    const start = vec3FromNodes(nodes.start);
    const end = vec3FromNodes(nodes.end);
    if (!start || !end) return null;
    return { start, end };
  }
  if (nodes.bottom && nodes.top) {
    const start = vec3FromNodes(nodes.bottom);
    const end = vec3FromNodes(nodes.top);
    if (!start || !end) return null;
    return { start, end };
  }
  return null;
}

export function memberLengthFromNodesM(element: ProjectElementMm): number | null {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;
  return ep.start.distanceTo(ep.end) * MM_TO_M;
}

function quaternionAlongDirection(
  direction: THREE.Vector3,
  rollRad: number,
): THREE.Quaternion {
  const dir = direction.clone();
  const len = dir.length();
  if (len < 1e-9) {
    return new THREE.Quaternion();
  }
  dir.divideScalar(len);

  const q = new THREE.Quaternion();
  const dot = LOCAL_LENGTH_AXIS.dot(dir);
  if (dot > 1 - 1e-6) {
    q.identity();
  } else if (dot < -1 + 1e-6) {
    q.setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI);
  } else {
    q.setFromUnitVectors(LOCAL_LENGTH_AXIS, dir);
  }

  if (Math.abs(rollRad) > 1e-9) {
    const qRoll = new THREE.Quaternion().setFromAxisAngle(LOCAL_LENGTH_AXIS, rollRad);
    q.multiply(qRoll);
  }

  return q;
}

function memberRollRad(element: ProjectElementMm): number {
  if (element.element_type === "purlin") {
    const euler = element.rotation_euler_deg;
    if (euler && euler.length >= 1) {
      return (euler[0] ?? 0) * DEG_TO_RAD;
    }
  }
  return 0;
}

export type MemberNodeFrame = {
  centerM: [number, number, number];
  lengthM: number;
  quaternion: [number, number, number, number];
  alignOffsetM: [number, number, number];
};

export function hasNodeDrivenFrame(element: ProjectElementMm): boolean {
  return memberEndpointsMm(element) !== null;
}

export function memberNodeFrame(element: ProjectElementMm): MemberNodeFrame | null {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;

  const startM = ep.start.clone().multiplyScalar(MM_TO_M);
  const endM = ep.end.clone().multiplyScalar(MM_TO_M);
  const direction = endM.clone().sub(startM);
  const lengthM = direction.length();
  if (lengthM < 1e-6) return null;

  const center = startM.add(endM).multiplyScalar(0.5);
  const q = quaternionAlongDirection(direction, memberRollRad(element));
  const align = meshAlignmentOffsetLocal(element);

  const centerM: [number, number, number] = [center.x, center.y, center.z];
  const quaternion: [number, number, number, number] = [q.x, q.y, q.z, q.w];
  if (
    !centerM.every(isFiniteCoord) ||
    !quaternion.every(isFiniteCoord) ||
    !align.every(isFiniteCoord) ||
    !Number.isFinite(lengthM)
  ) {
    return null;
  }

  return {
    centerM,
    lengthM,
    quaternion,
    alignOffsetM: align,
  };
}

export function applyMemberLocalToWorldM(
  element: ProjectElementMm,
  local: [number, number, number],
  includeAlignment: boolean,
): [number, number, number] | null {
  const frame = memberNodeFrame(element);
  if (!frame) return null;

  const v = new THREE.Vector3(...local);
  const userRot = ((element.rotation ?? 0) * DEG_TO_RAD);
  if (userRot !== 0) {
    v.applyAxisAngle(LOCAL_LENGTH_AXIS, userRot);
  }
  if (includeAlignment) {
    v.add(new THREE.Vector3(...frame.alignOffsetM));
  }
  const q = new THREE.Quaternion(...frame.quaternion);
  v.applyQuaternion(q);
  v.add(new THREE.Vector3(...frame.centerM));
  return [v.x, v.y, v.z];
}

export function memberObbCornersWorldM(
  element: ProjectElementMm,
  frame: MemberNodeFrame,
): THREE.Vector3[] {
  const { height, width } = crossSectionDimensionsM(element);
  const hl = frame.lengthM * 0.5;
  const hh = height * 0.5;
  const hw = width * 0.5;

  const localCorners = [
    new THREE.Vector3(-hl, -hh, -hw),
    new THREE.Vector3(hl, -hh, -hw),
    new THREE.Vector3(-hl, hh, -hw),
    new THREE.Vector3(-hl, -hh, hw),
    new THREE.Vector3(hl, hh, -hw),
    new THREE.Vector3(hl, -hh, hw),
    new THREE.Vector3(-hl, hh, hw),
    new THREE.Vector3(hl, hh, hw),
  ];

  const q = new THREE.Quaternion(...frame.quaternion);
  const center = new THREE.Vector3(...frame.centerM);
  const align = new THREE.Vector3(...frame.alignOffsetM);
  const userRot = ((element.rotation ?? 0) * DEG_TO_RAD);

  return localCorners.map((corner) => {
    const p = corner.clone();
    if (userRot !== 0) {
      p.applyAxisAngle(LOCAL_LENGTH_AXIS, userRot);
    }
    p.add(align);
    p.applyQuaternion(q);
    p.add(center);
    return p;
  });
}

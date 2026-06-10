import * as THREE from "three";

export const VIEWPORT_PICK_ROLE = {
  ELEMENT: "element",
  BACKGROUND: "background",
  GRID_FRAME: "grid_frame",
} as const;

export type ViewportPickTarget =
  | { type: typeof VIEWPORT_PICK_ROLE.ELEMENT; elementId: string }
  | { type: typeof VIEWPORT_PICK_ROLE.BACKGROUND }
  | { type: typeof VIEWPORT_PICK_ROLE.GRID_FRAME; frameIndex: number };

export function viewportPickTargetFromObject(
  object: THREE.Object3D,
): ViewportPickTarget | null {
  let current: THREE.Object3D | null = object;
  while (current) {
    const elementId = current.userData?.elementId;
    if (typeof elementId === "string" && elementId.length > 0) {
      return { type: VIEWPORT_PICK_ROLE.ELEMENT, elementId };
    }
    if (current.userData?.viewportPickRole === VIEWPORT_PICK_ROLE.BACKGROUND) {
      return { type: VIEWPORT_PICK_ROLE.BACKGROUND };
    }
    if (current.userData?.viewportPickRole === VIEWPORT_PICK_ROLE.GRID_FRAME) {
      const frameIndex = current.userData?.frameIndex;
      if (typeof frameIndex === "number") {
        return { type: VIEWPORT_PICK_ROLE.GRID_FRAME, frameIndex };
      }
    }
    current = current.parent;
  }
  return null;
}

export function viewportPickTargetFromHits(
  hits: THREE.Intersection[],
): ViewportPickTarget | null {
  for (const hit of hits) {
    const target = viewportPickTargetFromObject(hit.object);
    if (target?.type === VIEWPORT_PICK_ROLE.GRID_FRAME) {
      return target;
    }
  }
  for (const hit of hits) {
    const target = viewportPickTargetFromObject(hit.object);
    if (target?.type === VIEWPORT_PICK_ROLE.ELEMENT) {
      return target;
    }
  }
  for (const hit of hits) {
    const target = viewportPickTargetFromObject(hit.object);
    if (target?.type === VIEWPORT_PICK_ROLE.BACKGROUND) {
      return target;
    }
  }
  return null;
}

import * as THREE from "three";

export const VIEWPORT_PICK_ROLE = {
  ELEMENT: "element",
  BACKGROUND: "background",
  GRID_FRAME: "grid_frame",
  GRID_BAY: "grid_bay",
  WALL_PANEL: "wall_panel",
} as const;

export type ViewportPickTarget =
  | { type: typeof VIEWPORT_PICK_ROLE.ELEMENT; elementId: string }
  | { type: typeof VIEWPORT_PICK_ROLE.BACKGROUND }
  | { type: typeof VIEWPORT_PICK_ROLE.GRID_FRAME; frameIndex: number }
  | { type: typeof VIEWPORT_PICK_ROLE.GRID_BAY; bayIndex: number }
  | {
      type: typeof VIEWPORT_PICK_ROLE.WALL_PANEL;
      wallXLabel: string;
      bayIndex: number;
      side: "A" | "B";
    };

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
    if (current.userData?.viewportPickRole === VIEWPORT_PICK_ROLE.GRID_BAY) {
      const bayIndex = current.userData?.bayIndex;
      if (typeof bayIndex === "number") {
        return { type: VIEWPORT_PICK_ROLE.GRID_BAY, bayIndex };
      }
    }
    if (current.userData?.viewportPickRole === VIEWPORT_PICK_ROLE.WALL_PANEL) {
      const wallXLabel = current.userData?.wallXLabel;
      const bayIndex = current.userData?.bayIndex;
      const side = current.userData?.side;
      if (
        typeof wallXLabel === "string" &&
        typeof bayIndex === "number" &&
        (side === "A" || side === "B")
      ) {
        return {
          type: VIEWPORT_PICK_ROLE.WALL_PANEL,
          wallXLabel,
          bayIndex,
          side,
        };
      }
    }
    current = current.parent;
  }
  return null;
}

/** Closest structural member hit — ignores grid bays and background planes. */
export function viewportPickElementFromHits(
  hits: THREE.Intersection[],
): { type: typeof VIEWPORT_PICK_ROLE.ELEMENT; elementId: string } | null {
  for (const hit of hits) {
    const target = viewportPickTargetFromObject(hit.object);
    if (target?.type === VIEWPORT_PICK_ROLE.ELEMENT) {
      return target;
    }
  }
  return null;
}

export function viewportPickTargetFromHits(
  hits: THREE.Intersection[],
  options?: { preferWallPanel?: boolean },
): ViewportPickTarget | null {
  if (options?.preferWallPanel) {
    for (const hit of hits) {
      const target = viewportPickTargetFromObject(hit.object);
      if (target?.type === VIEWPORT_PICK_ROLE.WALL_PANEL) {
        return target;
      }
    }
  }
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
    if (target?.type === VIEWPORT_PICK_ROLE.GRID_BAY) {
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

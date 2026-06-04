import * as THREE from "three";

/**
 * Symmetric I-section centered at origin in the shape plane.
 * h = overall depth, b = flange width, tw = web, tf = flange thickness.
 * Shape coords: X = width (b), Y = height (h).
 */
export function createISectionShape(
  h: number,
  b: number,
  tw: number,
  tf: number,
): THREE.Shape {
  const hw = h / 2;
  const bw = b / 2;
  const tw2 = tw / 2;

  const shape = new THREE.Shape();
  shape.moveTo(-bw, -hw);
  shape.lineTo(bw, -hw);
  shape.lineTo(bw, -hw + tf);
  shape.lineTo(tw2, -hw + tf);
  shape.lineTo(tw2, hw - tf);
  shape.lineTo(bw, hw - tf);
  shape.lineTo(bw, hw);
  shape.lineTo(-bw, hw);
  shape.lineTo(-bw, hw - tf);
  shape.lineTo(-tw2, hw - tf);
  shape.lineTo(-tw2, -hw + tf);
  shape.lineTo(-bw, -hw + tf);
  shape.closePath();

  return shape;
}

export type ExtrusionAxis = "x" | "y" | "z";

/**
 * Build I-beam geometry in member-local space:
 *   +X = length (0 → length)
 *   +Y = cross-section height (centered on axis)
 *   +Z = cross-section width (centered on axis)
 *
 * No world-axis rotation or alignment offsets — the R3F group hierarchy handles that.
 */
export function createMemberLocalIBeamGeometry(
  h: number,
  b: number,
  tw: number,
  tf: number,
  length: number,
): THREE.ExtrudeGeometry {
  const shape = createISectionShape(h, b, tw, tf);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: length,
    bevelEnabled: false,
  });

  // Default extrusion is +Z; rotate so length runs +X.
  geometry.rotateY(Math.PI / 2);
  geometry.computeBoundingBox();
  const box = geometry.boundingBox!;
  const centerY = (box.min.y + box.max.y) * 0.5;
  const centerZ = (box.min.z + box.max.z) * 0.5;
  geometry.translate(-box.min.x, -centerY, -centerZ);

  return geometry;
}

/** Euler rotation mapping member-local +X (length) to the world axis for this member. */
export function memberAxisRotation(axis: ExtrusionAxis): [number, number, number] {
  switch (axis) {
    case "x":
      // local +X → world +X
      return [0, 0, 0];
    case "y":
      // local +X → world +Y (vertical column)
      return [0, 0, Math.PI / 2];
    case "z":
      // local +X → world +Z (negative Y rotation; +PI/2 would extrude along -Z)
      return [0, -Math.PI / 2, 0];
    default:
      return [0, 0, 0];
  }
}

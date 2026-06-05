import * as THREE from "three";

/**
 * Cross-section shape builders for non-I sections, in the shape plane:
 *   X = width (b), Y = height (h), centered on origin.
 *
 * Each is extruded along member-local +X by `extrudeSection`, matching the
 * I-beam convention in iSectionShape.ts (length runs +X, section centered on YZ).
 */

/** Rectangular hollow section (RHS/SHS): outer h×b, uniform wall t. */
export function createRhsShape(h: number, b: number, t: number): THREE.Shape {
  const hw = h / 2;
  const bw = b / 2;
  const shape = new THREE.Shape();
  shape.moveTo(-bw, -hw);
  shape.lineTo(bw, -hw);
  shape.lineTo(bw, hw);
  shape.lineTo(-bw, hw);
  shape.closePath();

  const ihw = Math.max(hw - t, 1e-4);
  const ibw = Math.max(bw - t, 1e-4);
  const hole = new THREE.Path();
  hole.moveTo(-ibw, -ihw);
  hole.lineTo(ibw, -ihw);
  hole.lineTo(ibw, ihw);
  hole.lineTo(-ibw, ihw);
  hole.closePath();
  shape.holes.push(hole);
  return shape;
}

/** Circular hollow section (CHS): outer diameter d, wall t. */
export function createChsShape(d: number, t: number): THREE.Shape {
  const ro = d / 2;
  const ri = Math.max(ro - t, 1e-4);
  const shape = new THREE.Shape();
  shape.absarc(0, 0, ro, 0, Math.PI * 2, false);
  const hole = new THREE.Path();
  hole.absarc(0, 0, ri, 0, Math.PI * 2, true);
  shape.holes.push(hole);
  return shape;
}

/** Equal/unequal angle (L): legs of length h (vertical) and b (horizontal), thickness t. */
export function createAngleShape(h: number, b: number, t: number): THREE.Shape {
  // Place the heel at the centroid-ish origin: center the bounding box.
  const x0 = -b / 2;
  const y0 = -h / 2;
  const shape = new THREE.Shape();
  shape.moveTo(x0, y0);
  shape.lineTo(x0 + b, y0);
  shape.lineTo(x0 + b, y0 + t);
  shape.lineTo(x0 + t, y0 + t);
  shape.lineTo(x0 + t, y0 + h);
  shape.lineTo(x0, y0 + h);
  shape.closePath();
  return shape;
}

/** Tee (T): flange width b × thickness tf on top, web tw × (h - tf) below. */
export function createTeeShape(h: number, b: number, tw: number, tf: number): THREE.Shape {
  const hw = h / 2;
  const bw = b / 2;
  const tww = tw / 2;
  const shape = new THREE.Shape();
  // Flange (top band) + web (down the middle).
  shape.moveTo(-bw, hw);
  shape.lineTo(bw, hw);
  shape.lineTo(bw, hw - tf);
  shape.lineTo(tww, hw - tf);
  shape.lineTo(tww, -hw);
  shape.lineTo(-tww, -hw);
  shape.lineTo(-tww, hw - tf);
  shape.lineTo(-bw, hw - tf);
  shape.closePath();
  return shape;
}

/**
 * Lipped or plain channel (Cee / UPN / UPE): web height h, flange width b,
 * wall thickness t, optional return lip length `lip` (0 = plain channel).
 * Built in raw coords; extrudeSection re-centers the section.
 */
export function createCeeShape(
  h: number,
  b: number,
  t: number,
  lip = 0,
): THREE.Shape {
  const shape = new THREE.Shape();
  if (lip > t) {
    shape.moveTo(0, 0);
    shape.lineTo(b, 0);
    shape.lineTo(b, lip);
    shape.lineTo(b - t, lip);
    shape.lineTo(b - t, t);
    shape.lineTo(t, t);
    shape.lineTo(t, h - t);
    shape.lineTo(b - t, h - t);
    shape.lineTo(b - t, h - lip);
    shape.lineTo(b, h - lip);
    shape.lineTo(b, h);
    shape.lineTo(0, h);
  } else {
    shape.moveTo(0, 0);
    shape.lineTo(b, 0);
    shape.lineTo(b, t);
    shape.lineTo(t, t);
    shape.lineTo(t, h - t);
    shape.lineTo(b, h - t);
    shape.lineTo(b, h);
    shape.lineTo(0, h);
  }
  shape.closePath();
  return shape;
}

/**
 * Lipped or plain Zed (Z purlin/girt): web height h, flange width b, wall
 * thickness t, optional return lip `lip`. Top flange runs +x, bottom flange -x.
 */
export function createZedShape(
  h: number,
  b: number,
  t: number,
  lip = 0,
): THREE.Shape {
  const shape = new THREE.Shape();
  if (lip > t) {
    shape.moveTo(t - b, 0);
    shape.lineTo(t, 0);
    shape.lineTo(t, h - t);
    shape.lineTo(b - t, h - t);
    shape.lineTo(b - t, h - lip);
    shape.lineTo(b, h - lip);
    shape.lineTo(b, h);
    shape.lineTo(0, h);
    shape.lineTo(0, t);
    shape.lineTo(2 * t - b, t);
    shape.lineTo(2 * t - b, lip);
    shape.lineTo(t - b, lip);
  } else {
    shape.moveTo(t - b, 0);
    shape.lineTo(t, 0);
    shape.lineTo(t, h - t);
    shape.lineTo(b, h - t);
    shape.lineTo(b, h);
    shape.lineTo(0, h);
    shape.lineTo(0, t);
    shape.lineTo(t - b, t);
  }
  shape.closePath();
  return shape;
}

/**
 * Extrude a shape-plane section along member-local +X, centered on the local
 * origin (same convention as createMemberLocalIBeamGeometry).
 */
export function extrudeSection(
  shape: THREE.Shape,
  length: number,
): THREE.ExtrudeGeometry {
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: length,
    bevelEnabled: false,
  });
  geometry.rotateY(Math.PI / 2);
  geometry.computeBoundingBox();
  const box = geometry.boundingBox!;
  const centerY = (box.min.y + box.max.y) * 0.5;
  const centerZ = (box.min.z + box.max.z) * 0.5;
  geometry.translate(-box.min.x - length * 0.5, -centerY, -centerZ);
  return geometry;
}

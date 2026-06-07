"use client";

import { useMemo } from "react";
import * as THREE from "three";

import { memberLengthM } from "@/lib/coordinates";
import { isFiniteNumber } from "@/lib/elementValidation";
import { purlinGeometryFlipZ, wallGirtGeometryFlipZ } from "@/lib/memberFrame";
import {
  createAngleShape,
  createCeeShape,
  createChsShape,
  createRhsShape,
  createTeeShape,
  createZedShape,
  extrudeSection,
} from "@/lib/sectionShapes";
import type { ProjectElementMm, SectionDimensionsMm } from "@/types/project";

const MM_TO_M = 0.001;

interface SectionExtrudedMeshProps {
  element: ProjectElementMm;
  section: SectionDimensionsMm;
  color: string;
}

/** True cross-section extrusion for RHS/SHS, CHS, Angle (L) and Tee (T) sections. */
export function SectionExtrudedMesh({
  element,
  section,
  color,
}: SectionExtrudedMeshProps) {
  const lengthM = memberLengthM(element);

  const geometry = useMemo<THREE.ExtrudeGeometry | null>(() => {
    if (!isFiniteNumber(lengthM) || lengthM < 1e-6) {
      return null;
    }
    const h = section.h * MM_TO_M;
    const b = section.b * MM_TO_M;
    const tw = section.tw * MM_TO_M;
    const tf = section.tf * MM_TO_M;
    const t = (section.t ?? section.tw) * MM_TO_M;
    const d = (section.d ?? section.h) * MM_TO_M;
    const lip = (section.lip ?? 0) * MM_TO_M;

    switch (element.shape_type) {
      case "RHS":
        return extrudeSection(createRhsShape(h, b, t), lengthM);
      case "CHS":
        return extrudeSection(createChsShape(d, t), lengthM);
      case "Pipe":
        // Solid rods (and pipes) — wall >= radius collapses to a solid cylinder.
        return extrudeSection(createChsShape(d, Math.min(t, d / 2)), lengthM);
      case "Angle":
        return extrudeSection(createAngleShape(h, b, t), lengthM);
      case "Tee":
        return extrudeSection(createTeeShape(h, b, tw, tf), lengthM);
      case "C-channel": {
        const geometry = extrudeSection(createCeeShape(h, b, t, lip), lengthM);
        if (wallGirtGeometryFlipZ(element) || purlinGeometryFlipZ(element)) {
          geometry.scale(1, 1, -1);
        }
        return geometry;
      }
      case "Zed":
        return extrudeSection(createZedShape(h, b, t, lip), lengthM);
      default:
        return null;
    }
  }, [
    element,
    element.shape_type,
    lengthM,
    section.h,
    section.b,
    section.tw,
    section.tf,
    section.t,
    section.d,
    section.lip,
  ]);

  if (!geometry) {
    return null;
  }

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={color} metalness={0.4} roughness={0.45} />
    </mesh>
  );
}

const SECTION_SHAPES: ReadonlySet<string> = new Set([
  "RHS",
  "CHS",
  "Pipe",
  "Angle",
  "Tee",
  "C-channel",
  "Zed",
]);

export function isSectionExtruded(element: ProjectElementMm): boolean {
  return (
    SECTION_SHAPES.has(element.shape_type) &&
    element.section_mm != null &&
    element.section_mm.h > 0 &&
    element.section_mm.b > 0
  );
}

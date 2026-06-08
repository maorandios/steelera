"use client";

import { useMemo } from "react";
import * as THREE from "three";

import { SteelMeshMaterial } from "@/components/viewport/SteelMeshMaterial";
import { memberLengthM } from "@/lib/coordinates";
import { isFiniteNumber } from "@/lib/elementValidation";
import type { ProjectElementMm } from "@/types/project";

const MM_TO_M = 0.001;

interface HaunchMeshProps {
  element: ProjectElementMm;
  color: string;
}

/**
 * Tapered wedge in member-local space (+X = length):
 *   top face at y = 0 (seated on rafter bottom flange),
 *   depth grows downward (negative y), deep at start, shallow at end.
 */
export function HaunchMesh({ element, color }: HaunchMeshProps) {
  const lengthM = memberLengthM(element);
  const startDepthM = (element.depth_mm ?? 0) * MM_TO_M;
  const endDepthM = (element.taper_end_depth_mm ?? element.depth_mm ?? 0) * MM_TO_M;
  const widthM = (element.width_mm ?? element.depth_mm ?? 0) * MM_TO_M;

  const geometry = useMemo(() => {
    const hl = lengthM / 2;
    const w2 = widthM / 2;

    // Top at y=0; bottom hangs down. Start face (deep) at x=-hl, end (shallow) at x=+hl.
    const v = [
      [-hl, 0, -w2],
      [-hl, 0, w2],
      [-hl, -startDepthM, -w2],
      [-hl, -startDepthM, w2],
      [hl, 0, -w2],
      [hl, 0, w2],
      [hl, -endDepthM, -w2],
      [hl, -endDepthM, w2],
    ];
    const positions = new Float32Array(v.flat());
    const index = [
      0, 1, 2, 1, 3, 2, // start face
      4, 6, 5, 5, 6, 7, // end face
      0, 4, 5, 0, 5, 1, // top
      2, 3, 7, 2, 7, 6, // bottom
      0, 2, 6, 0, 6, 4, // -z side
      1, 5, 7, 1, 7, 3, // +z side
    ];
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setIndex(index);
    geo.computeVertexNormals();
    return geo;
  }, [lengthM, widthM, startDepthM, endDepthM]);

  if (
    !isFiniteNumber(lengthM) ||
    lengthM < 1e-6 ||
    !isFiniteNumber(startDepthM) ||
    startDepthM < 1e-6 ||
    !isFiniteNumber(widthM) ||
    widthM < 1e-6
  ) {
    return null;
  }

  return (
    <mesh geometry={geometry}>
      <SteelMeshMaterial color={color} />
    </mesh>
  );
}

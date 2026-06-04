"use client";

import { useMemo } from "react";

import { memberLengthM } from "@/lib/coordinates";
import { isFiniteNumber } from "@/lib/elementValidation";
import { createMemberLocalIBeamGeometry } from "@/lib/iSectionShape";
import type { ProjectElementMm, SectionDimensionsMm } from "@/types/project";

const MM_TO_M = 0.001;

interface IBeamExtrudedMeshProps {
  element: ProjectElementMm;
  section: SectionDimensionsMm;
  color: string;
}

export function IBeamExtrudedMesh({
  element,
  section,
  color,
}: IBeamExtrudedMeshProps) {
  const lengthM = memberLengthM(element);
  if (!isFiniteNumber(lengthM) || lengthM < 1e-6) {
    return null;
  }
  const h = section.h * MM_TO_M;
  const b = section.b * MM_TO_M;
  const tw = section.tw * MM_TO_M;
  const tf = section.tf * MM_TO_M;

  const geometry = useMemo(
    () => createMemberLocalIBeamGeometry(h, b, tw, tf, lengthM),
    [h, b, tw, tf, lengthM],
  );

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={color} metalness={0.4} roughness={0.45} />
    </mesh>
  );
}

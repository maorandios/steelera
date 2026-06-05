"use client";

import { IBeamExtrudedMesh } from "@/components/viewport/IBeamExtrudedMesh";
import { HaunchMesh } from "@/components/viewport/HaunchMesh";
import {
  SectionExtrudedMesh,
  isSectionExtruded,
} from "@/components/viewport/SectionExtrudedMesh";
import { ElementMeshGroup } from "@/components/viewport/ElementMeshGroup";
import { geometryExtentsM, memberLengthM } from "@/lib/coordinates";
import { isElementRenderable } from "@/lib/elementValidation";
import { hasNodeDrivenFrame } from "@/lib/memberFrame";
import { useProjectStore } from "@/store/project-store";
import { isExtrudedIBeam, type ProjectElementMm } from "@/types/project";

const SHAPE_COLORS: Record<string, string> = {
  "I-beam": "#5b9bd5",
  "C-channel": "#6b8cae",
  Box: "#8b9cb3",
  Pipe: "#9aa8bc",
  Plate: "#7d8694",
  Haunch: "#4f86c6",
  RHS: "#6f9bc3",
  CHS: "#7fa6c9",
  Angle: "#8896ad",
  Tee: "#6d8eb0",
  Zed: "#6b8cae",
};

const SELECTED_COLOR = "#38bdf8";

interface StructuralElementMeshProps {
  element: ProjectElementMm;
}

export function StructuralElementMesh({ element }: StructuralElementMeshProps) {
  if (!isElementRenderable(element)) {
    return null;
  }

  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const isSelected = selectedElementId === element.id;
  const baseColor = SHAPE_COLORS[element.shape_type] ?? "#71717a";
  const color = isSelected ? SELECTED_COLOR : baseColor;

  if (isExtrudedIBeam(element) && element.section_mm) {
    return (
      <ElementMeshGroup element={element}>
        <IBeamExtrudedMesh
          element={element}
          section={element.section_mm}
          color={color}
        />
      </ElementMeshGroup>
    );
  }

  if (element.shape_type === "Haunch") {
    return (
      <ElementMeshGroup element={element}>
        <HaunchMesh element={element} color={color} />
      </ElementMeshGroup>
    );
  }

  if (isSectionExtruded(element) && element.section_mm) {
    return (
      <ElementMeshGroup element={element}>
        <SectionExtrudedMesh
          element={element}
          section={element.section_mm}
          color={color}
        />
      </ElementMeshGroup>
    );
  }

  const { height, width } = geometryExtentsM(element);
  const length = memberLengthM(element);
  const centered = hasNodeDrivenFrame(element);
  if (!Number.isFinite(length) || length < 1e-6) {
    return null;
  }

  return (
    <ElementMeshGroup element={element}>
      <mesh position={centered ? [0, 0, 0] : [length / 2, 0, 0]}>
        <boxGeometry args={[length, height, width]} />
        <meshStandardMaterial color={color} metalness={0.35} roughness={0.55} />
      </mesh>
    </ElementMeshGroup>
  );
}

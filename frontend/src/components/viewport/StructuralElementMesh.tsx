"use client";

import { IBeamExtrudedMesh } from "@/components/viewport/IBeamExtrudedMesh";
import { ElementMeshGroup } from "@/components/viewport/ElementMeshGroup";
import { geometryExtentsM } from "@/lib/coordinates";
import { useProjectStore } from "@/store/project-store";
import { isExtrudedIBeam, type ProjectElementMm } from "@/types/project";

const SHAPE_COLORS: Record<string, string> = {
  "I-beam": "#94a3b8",
  "C-channel": "#64748b",
  Box: "#71717a",
  Pipe: "#a1a1aa",
};

const SELECTED_COLOR = "#38bdf8";

interface StructuralElementMeshProps {
  element: ProjectElementMm;
}

export function StructuralElementMesh({ element }: StructuralElementMeshProps) {
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

  const { length, height, width } = geometryExtentsM(element);

  return (
    <ElementMeshGroup element={element}>
      <mesh position={[length / 2, 0, 0]}>
        <boxGeometry args={[length, height, width]} />
        <meshStandardMaterial color={color} metalness={0.35} roughness={0.55} />
      </mesh>
    </ElementMeshGroup>
  );
}

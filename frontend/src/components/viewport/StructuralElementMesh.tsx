"use client";

import { IBeamExtrudedMesh } from "@/components/viewport/IBeamExtrudedMesh";
import { HaunchMesh } from "@/components/viewport/HaunchMesh";
import {
  SectionExtrudedMesh,
  isSectionExtruded,
} from "@/components/viewport/SectionExtrudedMesh";
import { ElementMeshGroup } from "@/components/viewport/ElementMeshGroup";
import { SteelMeshMaterial } from "@/components/viewport/SteelMeshMaterial";
import { geometryExtentsM, memberLengthM } from "@/lib/coordinates";
import { isElementRenderable } from "@/lib/elementValidation";
import { hasNodeDrivenFrame } from "@/lib/memberFrame";
import { viewportTheme } from "@/lib/viewport-theme";
import { useIsElementHighlighted } from "@/store/project-store";
import { isExtrudedIBeam, type ProjectElementMm } from "@/types/project";

interface StructuralElementMeshProps {
  element: ProjectElementMm;
}

export function StructuralElementMesh({ element }: StructuralElementMeshProps) {
  if (!isElementRenderable(element)) {
    return null;
  }

  const isSelected = useIsElementHighlighted(element.id);
  const baseColor =
    viewportTheme.steel.colors[element.shape_type] ?? viewportTheme.steel.default;
  const color = isSelected ? viewportTheme.steel.selected : baseColor;

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
        <SteelMeshMaterial color={color} />
      </mesh>
    </ElementMeshGroup>
  );
}

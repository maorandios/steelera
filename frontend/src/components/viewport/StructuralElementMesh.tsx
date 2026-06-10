"use client";

import { IBeamExtrudedMesh } from "@/components/viewport/IBeamExtrudedMesh";
import { HaunchMesh } from "@/components/viewport/HaunchMesh";
import {
  SectionExtrudedMesh,
  isSectionExtruded,
} from "@/components/viewport/SectionExtrudedMesh";
import { ElementMeshGroup } from "@/components/viewport/ElementMeshGroup";
import { MeshSchematicEdges } from "@/components/viewport/MeshSchematicEdges";
import { SteelMeshMaterial } from "@/components/viewport/SteelMeshMaterial";
import { geometryExtentsM, memberLengthM } from "@/lib/coordinates";
import { isElementRenderable } from "@/lib/elementValidation";
import { hasNodeDrivenFrame } from "@/lib/memberFrame";
import { elementDisplayColor } from "@/lib/element-display-color";
import { viewportTheme } from "@/lib/viewport-theme";
import { useIsElementHighlighted, useElementGhostOpacity } from "@/store/project-store";
import { isExtrudedIBeam, type ProjectElementMm } from "@/types/project";

interface StructuralElementMeshProps {
  element: ProjectElementMm;
}

export function StructuralElementMesh({ element }: StructuralElementMeshProps) {
  const isSelected = useIsElementHighlighted(element.id);
  const ghostOpacity = useElementGhostOpacity(element.id);

  if (!isElementRenderable(element)) {
    return null;
  }
  const baseColor = elementDisplayColor(element);
  const color = isSelected ? viewportTheme.steel.selected : baseColor;
  const matProps = {
    color,
    metalness: viewportTheme.steel.schematicMetalness,
    roughness: viewportTheme.steel.schematicRoughness,
    transparent: ghostOpacity < 1,
    opacity: ghostOpacity,
  };

  if (isExtrudedIBeam(element) && element.section_mm) {
    return (
      <ElementMeshGroup element={element}>
        <IBeamExtrudedMesh
          element={element}
          section={element.section_mm}
          {...matProps}
        />
      </ElementMeshGroup>
    );
  }

  if (element.shape_type === "Haunch") {
    return (
      <ElementMeshGroup element={element}>
        <HaunchMesh element={element} {...matProps} />
      </ElementMeshGroup>
    );
  }

  if (isSectionExtruded(element) && element.section_mm) {
    return (
      <ElementMeshGroup element={element}>
        <SectionExtrudedMesh
          element={element}
          section={element.section_mm}
          {...matProps}
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
        <SteelMeshMaterial
          {...matProps}
          depthWrite={ghostOpacity > 0.5}
        />
        {ghostOpacity > 0.5 && <MeshSchematicEdges />}
      </mesh>
    </ElementMeshGroup>
  );
}

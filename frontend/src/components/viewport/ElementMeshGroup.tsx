"use client";

import { Edges } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import type { ReactNode } from "react";

import {
  elementRotationRad,
  geometryExtentsM,
  macroEulerRotationRad,
  memberAxisRotationEuler,
  meshAlignmentOffsetLocal,
  structuralAxisOriginM,
} from "@/lib/coordinates";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface ElementMeshGroupProps {
  element: ProjectElementMm;
  children: ReactNode;
}

/**
 * Transform hierarchy (outer → inner):
 *   1. World position on structural axis
 *   2. Member axis orientation (local +X → world length direction)
 *   3. Macro Euler rotation (rotation_euler_deg) — rafter/purlin pitch in X
 *      TODO(rafter-pitch): fine-tune euler vs. catalog flange normals later.
 *   4. Alignment offset on local +Y (in pitched space, before section roll)
 *   5. User rotation around member-local +X
 *   6. Mesh geometry at member-local origin
 */
export function ElementMeshGroup({ element, children }: ElementMeshGroupProps) {
  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const selectElement = useProjectStore((state) => state.selectElement);
  const isSelected = selectedElementId === element.id;

  const [originX, originY, originZ] = structuralAxisOriginM(element);
  const axisRotation = memberAxisRotationEuler(element);
  const macroEuler = macroEulerRotationRad(element);
  const userRotation = elementRotationRad(element);
  const alignOffset = meshAlignmentOffsetLocal(element);
  const { length, height, width } = geometryExtentsM(element);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    selectElement(element.id);
  };

  return (
    <group position={[originX, originY, originZ]} onClick={handleClick}>
      <group rotation={axisRotation}>
        <group rotation={macroEuler}>
          <group position={alignOffset}>
            <group rotation={[userRotation, 0, 0]}>
              {children}
              {isSelected && (
                <mesh position={[length / 2, 0, 0]}>
                  <boxGeometry args={[length, height, width]} />
                  <meshBasicMaterial visible={false} />
                  <Edges color="#38bdf8" threshold={15} />
                </mesh>
              )}
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}

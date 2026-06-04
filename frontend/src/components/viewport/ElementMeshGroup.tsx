"use client";

import { Edges } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import { useMemo, type ReactNode } from "react";

import {
  elementRotationRad,
  geometryExtentsM,
  macroEulerRotationRad,
  memberAxisRotationEuler,
  meshAlignmentOffsetLocal,
  structuralAxisOriginM,
} from "@/lib/coordinates";
import { isElementRenderable } from "@/lib/elementValidation";
import { hasNodeDrivenFrame, memberNodeFrame } from "@/lib/memberFrame";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface ElementMeshGroupProps {
  element: ProjectElementMm;
  children: ReactNode;
}

/**
 * Node-driven frame (preferred): center + quaternion from start→end nodes.
 * Legacy fallback: axis origin + axis rotation + macro Euler for older payloads.
 */
export function ElementMeshGroup({ element, children }: ElementMeshGroupProps) {
  if (!isElementRenderable(element)) {
    return null;
  }

  const selectedElementId = useProjectStore((state) => state.selectedElementId);
  const selectElement = useProjectStore((state) => state.selectElement);
  const isSelected = selectedElementId === element.id;

  const nodeFrame = useMemo(
    () => (hasNodeDrivenFrame(element) ? memberNodeFrame(element) : null),
    [element],
  );

  const legacy = useMemo(() => {
    if (nodeFrame) return null;
    return {
      origin: structuralAxisOriginM(element),
      axisRotation: memberAxisRotationEuler(element),
      macroEuler: macroEulerRotationRad(element),
      userRotation: elementRotationRad(element),
      alignOffset: meshAlignmentOffsetLocal(element),
      extents: geometryExtentsM(element),
    };
  }, [element, nodeFrame]);

  const userRotation = elementRotationRad(element);
  const { height, width } = geometryExtentsM(element);
  const lengthM = nodeFrame?.lengthM ?? legacy?.extents.length ?? 0;
  if (!Number.isFinite(lengthM) || lengthM < 1e-6) {
    return null;
  }
  if (!Number.isFinite(height) || !Number.isFinite(width) || height < 1e-6 || width < 1e-6) {
    return null;
  }

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    selectElement(element.id);
  };

  if (nodeFrame) {
    return (
      <group position={nodeFrame.centerM} onClick={handleClick}>
        <group quaternion={nodeFrame.quaternion}>
          <group position={nodeFrame.alignOffsetM}>
            <group rotation={[userRotation, 0, 0]}>
              {children}
              {isSelected && (
                <mesh>
                  <boxGeometry args={[lengthM, height, width]} />
                  <meshBasicMaterial visible={false} />
                  <Edges color="#38bdf8" threshold={15} />
                </mesh>
              )}
            </group>
          </group>
        </group>
      </group>
    );
  }

  if (!legacy) return null;

  const [originX, originY, originZ] = legacy.origin;

  return (
    <group position={[originX, originY, originZ]} onClick={handleClick}>
      <group rotation={legacy.axisRotation}>
        <group rotation={legacy.macroEuler}>
          <group position={legacy.alignOffset}>
            <group rotation={[legacy.userRotation, 0, 0]}>
              {children}
              {isSelected && (
                <mesh position={[lengthM / 2, 0, 0]}>
                  <boxGeometry args={[lengthM, height, width]} />
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

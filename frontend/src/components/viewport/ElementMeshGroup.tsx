"use client";

import { Edges } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef, type ReactNode } from "react";
import * as THREE from "three";

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
import { VIEWPORT_PICK_ROLE } from "@/lib/viewport-pick";
import { viewportTheme } from "@/lib/viewport-theme";
import { useIsElementHighlighted, useSketchModeActive } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface ElementMeshGroupProps {
  element: ProjectElementMm;
  children: ReactNode;
}

const memberPickUserData = (elementId: string) => ({
  elementId,
  viewportPickRole: VIEWPORT_PICK_ROLE.ELEMENT,
});

/**
 * Node-driven frame (preferred): center + quaternion from start→end nodes.
 * Legacy fallback: axis origin + axis rotation + macro Euler for older payloads.
 */
const noopRaycast = () => {};

export function ElementMeshGroup({ element, children }: ElementMeshGroupProps) {
  const isSelected = useIsElementHighlighted(element.id);
  const sketchMode = useSketchModeActive();
  const groupRef = useRef<THREE.Group>(null);
  const savedRaycast = useRef(
    new WeakMap<THREE.Mesh, THREE.Mesh["raycast"]>(),
  );

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

  useLayoutEffect(() => {
    const group = groupRef.current;
    if (!group) return;
    group.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      if (sketchMode) {
        if (!savedRaycast.current.has(mesh)) {
          savedRaycast.current.set(mesh, mesh.raycast.bind(mesh));
        }
        mesh.raycast = noopRaycast;
      } else {
        const restore = savedRaycast.current.get(mesh);
        if (restore) mesh.raycast = restore;
      }
    });
  }, [sketchMode, element.id]);

  if (!isElementRenderable(element)) {
    return null;
  }

  const userRotation = elementRotationRad(element);
  const { height, width } = geometryExtentsM(element);
  const lengthM = nodeFrame?.lengthM ?? legacy?.extents.length ?? 0;
  const selectBoxPos: [number, number, number] =
    element.shape_type === "Haunch" ? [0, -height / 2, 0] : [0, 0, 0];
  if (!Number.isFinite(lengthM) || lengthM < 1e-6) {
    return null;
  }
  if (!Number.isFinite(height) || !Number.isFinite(width) || height < 1e-6 || width < 1e-6) {
    return null;
  }

  const pickMesh = (position: [number, number, number]) =>
    sketchMode ? null : (
      <mesh position={position} userData={memberPickUserData(element.id)}>
        <boxGeometry args={[lengthM, height, width]} />
        <meshBasicMaterial visible={false} />
        {isSelected && (
          <Edges color={viewportTheme.selection.edge} threshold={15} />
        )}
      </mesh>
    );

  if (nodeFrame) {
    return (
      <group
        ref={groupRef}
        position={nodeFrame.centerM}
        userData={memberPickUserData(element.id)}
      >
        <group quaternion={nodeFrame.quaternion}>
          <group position={nodeFrame.alignOffsetM}>
            <group rotation={[userRotation, 0, 0]}>
              {children}
              {pickMesh(selectBoxPos)}
            </group>
          </group>
        </group>
      </group>
    );
  }

  if (!legacy) return null;

  const [originX, originY, originZ] = legacy.origin;
  const legacyPickPos: [number, number, number] =
    element.shape_type === "Haunch" ? selectBoxPos : [lengthM / 2, 0, 0];

  return (
    <group
      ref={groupRef}
      position={[originX, originY, originZ]}
      userData={memberPickUserData(element.id)}
    >
      <group rotation={legacy.axisRotation}>
        <group rotation={legacy.macroEuler}>
          <group position={legacy.alignOffset}>
            <group rotation={[legacy.userRotation, 0, 0]}>
              {children}
              {pickMesh(legacyPickPos)}
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}

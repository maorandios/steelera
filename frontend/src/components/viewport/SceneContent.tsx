"use client";

import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { useMemo } from "react";

import { StructuralGrid } from "@/components/viewport/StructuralGrid";
import { StructuralElementMesh } from "@/components/viewport/StructuralElementMesh";
import { sceneStructuralBounds } from "@/lib/coordinates";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface SceneContentProps {
  projectElements: ProjectElementMm[];
}

export function SceneContent({ projectElements }: SceneContentProps) {
  const clearSelection = useProjectStore((state) => state.clearSelection);
  const structuralGrid = useProjectStore((state) => state.structuralGrid);

  const { center, size, minX, maxX, minZ, maxZ } = useMemo(() => {
    const bounds = sceneStructuralBounds(projectElements);
    const safeSize = Number.isFinite(bounds.size) ? bounds.size : 20;
    const safeCenter: [number, number, number] = bounds.center.every(Number.isFinite)
      ? bounds.center
      : [6, 2, 12];
    const half = safeSize / 2;
    return {
      center: safeCenter,
      size: safeSize,
      minX: safeCenter[0] - half,
      maxX: safeCenter[0] + half,
      minZ: safeCenter[2] - half,
      maxZ: safeCenter[2] + half,
    };
  }, [projectElements]);

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={[
          center[0] + size * 0.8,
          center[1] + size * 0.6,
          center[2] + size * 0.8,
        ]}
        fov={45}
      />
      <ambientLight intensity={0.5} />
      <directionalLight position={[15, 20, 10]} intensity={1} />
      <StructuralGrid
        xCoordsMm={structuralGrid.xCoordsMm}
        zCoordsMm={structuralGrid.zCoordsMm}
        extentMinX={minX}
        extentMaxX={maxX}
        extentMinZ={minZ}
        extentMaxZ={maxZ}
        onBackgroundClick={() => clearSelection()}
      />
      {projectElements.map((element) => (
        <StructuralElementMesh key={element.id} element={element} />
      ))}
      {projectElements.length === 0 && (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1, 0.05, 1]} />
          <meshStandardMaterial color="#27272a" transparent opacity={0.4} />
        </mesh>
      )}
      <OrbitControls target={center} enablePan enableZoom />
    </>
  );
}

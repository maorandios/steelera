"use client";

import { Grid, OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { useMemo } from "react";

import { StructuralElementMesh } from "@/components/viewport/StructuralElementMesh";
import { sceneStructuralBounds } from "@/lib/coordinates";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface SceneContentProps {
  projectElements: ProjectElementMm[];
}

export function SceneContent({ projectElements }: SceneContentProps) {
  const clearSelection = useProjectStore((state) => state.clearSelection);

  const { center, size } = useMemo(
    () => sceneStructuralBounds(projectElements),
    [projectElements],
  );

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
      <Grid
        args={[Math.max(30, size * 2), Math.max(30, size * 2)]}
        cellSize={1}
        sectionSize={5}
        fadeDistance={60}
        position={[center[0], 0, center[2]]}
        cellColor="#27272a"
        sectionColor="#3f3f46"
        onClick={() => clearSelection()}
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

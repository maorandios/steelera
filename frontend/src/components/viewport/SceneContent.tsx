"use client";

import { Grid, OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { useMemo } from "react";

import { StructuralElementMesh } from "@/components/viewport/StructuralElementMesh";
import type { ProjectState } from "@/types/project";

interface SceneContentProps {
  projectState: ProjectState;
}

export function SceneContent({ projectState }: SceneContentProps) {
  const { center, size } = useMemo(() => {
    const elements = projectState.elements;
    if (elements.length === 0) {
      return { center: [15, 6, 6] as [number, number, number], size: 30 };
    }

    let minX = Infinity;
    let minY = Infinity;
    let minZ = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    let maxZ = -Infinity;

    for (const el of elements) {
      const [x, y, z] = el.position;
      const [sx, sy, sz] = el.size;
      const hx = sx / 2;
      const hy = sy / 2;
      const hz = sz / 2;
      minX = Math.min(minX, x - hx);
      maxX = Math.max(maxX, x + hx);
      minY = Math.min(minY, y - hy);
      maxY = Math.max(maxY, y + hy);
      minZ = Math.min(minZ, z - hz);
      maxZ = Math.max(maxZ, z + hz);
    }

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const cz = (minZ + maxZ) / 2;
    const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);

    return {
      center: [cx, cz, cy] as [number, number, number],
      size: span,
    };
  }, [projectState.elements]);

  const hasElements = projectState.elements.length > 0;

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={[
          center[0] + size * 0.9,
          center[1] + size * 0.65,
          center[2] + size * 0.9,
        ]}
        fov={45}
      />
      <ambientLight intensity={0.45} />
      <directionalLight position={[20, 30, 10]} intensity={1.1} />
      <Grid
        args={[Math.max(40, size * 2), Math.max(40, size * 2)]}
        cellSize={1}
        sectionSize={5}
        fadeDistance={80}
        position={[center[0], 0, center[2]]}
        cellColor="#27272a"
        sectionColor="#3f3f46"
      />
      {projectState.elements.map((element) => (
        <StructuralElementMesh key={element.id} element={element} />
      ))}
      {!hasElements && (
        <mesh position={center}>
          <boxGeometry args={[2, 0.1, 2]} />
          <meshStandardMaterial color="#27272a" transparent opacity={0.5} />
        </mesh>
      )}
      <OrbitControls
        target={center}
        enablePan
        enableZoom
        maxPolarAngle={Math.PI / 2.05}
      />
    </>
  );
}

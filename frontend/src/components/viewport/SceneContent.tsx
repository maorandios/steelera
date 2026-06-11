"use client";

import { Environment, PerspectiveCamera } from "@react-three/drei";
import { useMemo } from "react";

import { GroundPlacementOverlay } from "@/components/viewport/GroundPlacementOverlay";
import { SteelMeshMaterial } from "@/components/viewport/SteelMeshMaterial";
import { StructuralGrid } from "@/components/viewport/StructuralGrid";
import { SchematicOverlay } from "@/components/viewport/SchematicOverlay";
import { StructuralElementMesh } from "@/components/viewport/StructuralElementMesh";
import { ViewportOrbitControls } from "@/components/viewport/ViewportOrbitControls";
import { ViewportPointerPicker } from "@/components/viewport/ViewportPointerPicker";
import { sceneStructuralBounds } from "@/lib/coordinates";
import { filterRenderableElements } from "@/lib/elementValidation";
import { viewportTheme } from "@/lib/viewport-theme";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

interface SceneContentProps {
  projectElements: ProjectElementMm[];
}

export function SceneContent({ projectElements }: SceneContentProps) {
  const structuralGrid = useProjectStore((state) => state.structuralGrid);
  const { lighting, environment, placeholder, performance } = viewportTheme;

  const renderableElements = useMemo(
    () => filterRenderableElements(projectElements),
    [projectElements],
  );

  const useHdrEnvironment =
    performance.enableEnvironment &&
    renderableElements.length <= performance.environmentMaxElements;

  const { center, size, minX, maxX, minZ, maxZ } = useMemo(() => {
    const bounds = sceneStructuralBounds(renderableElements);
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
  }, [renderableElements]);

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
      {useHdrEnvironment && (
        <Environment
          preset={environment.preset}
          environmentIntensity={environment.intensity}
        />
      )}
      <hemisphereLight args={["#f8fafc", "#cbd5e1", 0.55]} />
      <ambientLight intensity={lighting.ambient} />
      <directionalLight
        position={lighting.directionalPosition}
        intensity={lighting.directional}
        castShadow={performance.enableShadows}
      />
      {lighting.fill > 0 && (
        <directionalLight
          position={lighting.fillPosition}
          intensity={lighting.fill}
        />
      )}
      <StructuralGrid
        xCoordsMm={structuralGrid.xCoordsMm}
        zCoordsMm={structuralGrid.zCoordsMm}
        extentMinX={minX}
        extentMaxX={maxX}
        extentMinZ={minZ}
        extentMaxZ={maxZ}
      />
      {renderableElements.map((element) => (
        <StructuralElementMesh
          key={`${element.id}:${element.profile_name ?? ""}:${element.depth_mm}x${element.width_mm}`}
          element={element}
        />
      ))}
      <SchematicOverlay projectElements={renderableElements} />
      <GroundPlacementOverlay />
      {renderableElements.length === 0 && (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1, 0.05, 1]} />
          <SteelMeshMaterial color={placeholder} transparent opacity={0.55} />
        </mesh>
      )}
      <ViewportPointerPicker />
      <ViewportOrbitControls defaultTarget={center} />
    </>
  );
}

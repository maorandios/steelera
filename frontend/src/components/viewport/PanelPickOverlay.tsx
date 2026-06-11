"use client";

import { useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

import { buildBracingPanelsFromColumns } from "@/lib/bracing-panel-layout";
import {
  bracingPanelFromPickData,
  bracingPanelKey,
  type WallPanelPickData,
} from "@/lib/wall-panel";
import { VIEWPORT_PICK_ROLE } from "@/lib/viewport-pick";
import { useProjectStore } from "@/store/project-store";
import type { BracingPanel } from "@/types/add-element";

const MM_TO_M = 0.001;
const PICK_DEPTH_M = 0.15;

type PanelPickOverlayProps = {
  xCoordsMm: number[];
  zCoordsMm: number[];
  eaveHeightMm: number;
};

type PickMeshSpec = {
  key: string;
  panel: BracingPanel;
  position: [number, number, number];
  size: [number, number, number];
  pickData: WallPanelPickData;
};

function pickDataFromPanel(panel: BracingPanel): WallPanelPickData {
  if (panel.kind === "gable_wall") {
    return {
      panelKind: "gable_wall",
      gableEnd: panel.end,
      frameIndex: panel.frameIndex,
      xBayIndex: panel.xBayIndex,
      x0Mm: panel.x0Mm,
      x1Mm: panel.x1Mm,
      zMm: panel.zMm,
    };
  }
  return {
    panelKind: "long_wall",
    side: panel.side,
    wallXLabel: panel.wallXLabel,
    bayIndex: panel.bayIndex,
    z0Mm: panel.z0Mm,
    z1Mm: panel.z1Mm,
    xMm: panel.xMm,
  };
}

function panelFromUserData(
  userData: THREE.Object3D["userData"],
  grid: ReturnType<typeof useProjectStore.getState>["structuralGrid"],
): BracingPanel | null {
  if (userData?.viewportPickRole !== VIEWPORT_PICK_ROLE.WALL_PANEL) {
    return null;
  }
  return bracingPanelFromPickData(userData as WallPanelPickData, grid);
}

export function PanelPickOverlay({
  xCoordsMm,
  zCoordsMm,
  eaveHeightMm,
}: PanelPickOverlayProps) {
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const projectElements = useProjectStore((s) => s.projectElements);
  const hoveredWallPanel = useProjectStore((s) => s.hoveredWallPanel);
  const setHoveredWallPanel = useProjectStore((s) => s.setHoveredWallPanel);
  const structuralGrid = useProjectStore((s) => s.structuralGrid);
  const { gl, camera, scene } = useThree();

  const active = viewportMode === "pick_panel";
  const eaveM = Math.max(eaveHeightMm * MM_TO_M, 0.5);

  const panels = useMemo((): PickMeshSpec[] => {
    const gridState = { ...structuralGrid, xCoordsMm, zCoordsMm };
    const bracingPanels = buildBracingPanelsFromColumns(
      projectElements,
      gridState,
    );

    return bracingPanels.map((panel) => {
      if (panel.kind === "long_wall") {
        const z0M = panel.z0Mm * MM_TO_M;
        const z1M = panel.z1Mm * MM_TO_M;
        const depth = Math.max(z1M - z0M, 0.4);
        return {
          key: bracingPanelKey(panel),
          panel,
          position: [panel.xMm * MM_TO_M, eaveM / 2, (z0M + z1M) / 2],
          size: [PICK_DEPTH_M, eaveM, depth],
          pickData: pickDataFromPanel(panel),
        };
      }

      const x0M = panel.x0Mm * MM_TO_M;
      const x1M = panel.x1Mm * MM_TO_M;
      const width = Math.max(x1M - x0M, 0.4);
      return {
        key: bracingPanelKey(panel),
        panel,
        position: [(x0M + x1M) / 2, eaveM / 2, panel.zMm * MM_TO_M],
        size: [width, eaveM, PICK_DEPTH_M],
        pickData: pickDataFromPanel(panel),
      };
    });
  }, [projectElements, structuralGrid, xCoordsMm, zCoordsMm, eaveM]);

  useEffect(() => {
    if (!active) {
      setHoveredWallPanel(null);
      return undefined;
    }

    const raycaster = new THREE.Raycaster();
    raycaster.params.Line.threshold = 0.02;
    const pointer = new THREE.Vector2();
    const gridState = useProjectStore.getState().structuralGrid;

    const onPointerMove = (event: PointerEvent) => {
      const rect = gl.domElement.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) {
        return;
      }
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(scene.children, true);
      let found: BracingPanel | null = null;
      for (const hit of hits) {
        let current: THREE.Object3D | null = hit.object;
        while (current) {
          const panel = panelFromUserData(current.userData, gridState);
          if (panel) {
            found = panel;
            break;
          }
          current = current.parent;
        }
        if (found) break;
      }
      const prev = useProjectStore.getState().hoveredWallPanel;
      const nextKey = found ? bracingPanelKey(found) : null;
      const prevKey = prev ? bracingPanelKey(prev) : null;
      if (nextKey !== prevKey) {
        setHoveredWallPanel(found);
      }
    };

    gl.domElement.addEventListener("pointermove", onPointerMove);
    return () => {
      gl.domElement.removeEventListener("pointermove", onPointerMove);
    };
  }, [active, camera, gl, scene, setHoveredWallPanel]);

  useEffect(() => {
    if (!active) return undefined;
    gl.domElement.style.cursor = "crosshair";
    return () => {
      gl.domElement.style.cursor = "";
    };
  }, [active, gl]);

  if (!active || panels.length === 0) {
    return null;
  }

  const hoveredKey = hoveredWallPanel ? bracingPanelKey(hoveredWallPanel) : null;

  return (
    <group>
      {panels.map((entry) => {
        const highlighted = hoveredKey === entry.key;
        return (
          <group key={entry.key}>
            <mesh
              position={entry.position}
              userData={{
                viewportPickRole: VIEWPORT_PICK_ROLE.WALL_PANEL,
                ...entry.pickData,
              }}
            >
              <boxGeometry args={entry.size} />
              <meshBasicMaterial visible={false} />
            </mesh>
            {highlighted ? (
              <mesh position={entry.position}>
                <boxGeometry
                  args={[
                    entry.size[0] * 1.04,
                    entry.size[1] * 1.02,
                    entry.size[2] * 1.04,
                  ]}
                />
                <meshBasicMaterial
                  transparent
                  opacity={0.25}
                  color="#3b82f6"
                  depthWrite={false}
                />
              </mesh>
            ) : null}
          </group>
        );
      })}
    </group>
  );
}

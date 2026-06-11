"use client";

import { useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

import { buildBracingPanelsFromColumns } from "@/lib/bracing-panel-layout";
import {
  computeRoofGeometry,
  roofPanelCornersMm,
  type RoofPanelCornerMm,
} from "@/lib/roof-panel-layout";
import type { ShedAssemblyParams } from "@/lib/shed-assembly";
import {
  bracingPanelFromPickData,
  bracingPanelKey,
  type WallPanelPickData,
} from "@/lib/wall-panel";
import { VIEWPORT_PICK_ROLE } from "@/lib/viewport-pick";
import { useProjectStore } from "@/store/project-store";
import type { BracingPanel, RoofPanel } from "@/types/add-element";

const MM_TO_M = 0.001;
const PICK_DEPTH_M = 0.15;
const ROOF_PICK_THICKNESS_M = 0.25;

type PanelPickOverlayProps = {
  xCoordsMm: number[];
  zCoordsMm: number[];
  eaveHeightMm: number;
  roofParams?: Pick<
    ShedAssemblyParams,
    "height" | "roof_style" | "roof_pitch_deg" | "mono_high_side"
  > | null;
};

type WallPickMeshSpec = {
  kind: "wall";
  key: string;
  panel: BracingPanel;
  position: [number, number, number];
  size: [number, number, number];
  pickData: WallPanelPickData;
};

type RoofPickMeshSpec = {
  kind: "roof";
  key: string;
  panel: RoofPanel;
  position: [number, number, number];
  quaternion: THREE.Quaternion;
  size: [number, number, number];
  pickData: WallPanelPickData;
};

type PickMeshSpec = WallPickMeshSpec | RoofPickMeshSpec;

function pickDataFromPanel(panel: BracingPanel): WallPanelPickData {
  if (panel.kind === "roof") {
    return {
      panelKind: "roof",
      slopeSide: panel.slopeSide,
      slopeIndex: panel.slopeIndex,
      roofBayIndex: panel.bayIndex,
      z0Mm: panel.z0Mm,
      z1Mm: panel.z1Mm,
    };
  }
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

function roofPickTransform(corners: [
  RoofPanelCornerMm,
  RoofPanelCornerMm,
  RoofPanelCornerMm,
  RoofPanelCornerMm,
]): {
  position: [number, number, number];
  quaternion: THREE.Quaternion;
  size: [number, number, number];
} {
  const toM = (point: RoofPanelCornerMm) =>
    new THREE.Vector3(point.x * MM_TO_M, point.y * MM_TO_M, point.z * MM_TO_M);

  const p0 = toM(corners[0]);
  const p1 = toM(corners[1]);
  const p2 = toM(corners[2]);
  const p3 = toM(corners[3]);

  const center = new THREE.Vector3()
    .add(p0)
    .add(p1)
    .add(p2)
    .add(p3)
    .multiplyScalar(0.25);

  const u = new THREE.Vector3().subVectors(p2, p0);
  const v = new THREE.Vector3().subVectors(p1, p0);
  const width = Math.max(u.length(), 0.4);
  const depth = Math.max(v.length(), 0.4);
  u.normalize();
  v.normalize();
  const normal = new THREE.Vector3().crossVectors(u, v).normalize();
  const matrix = new THREE.Matrix4().makeBasis(u, v, normal);
  const quaternion = new THREE.Quaternion().setFromRotationMatrix(matrix);

  return {
    position: [center.x, center.y, center.z],
    quaternion,
    size: [width, depth, ROOF_PICK_THICKNESS_M],
  };
}

function panelFromUserData(
  userData: THREE.Object3D["userData"],
  grid: ReturnType<typeof useProjectStore.getState>["structuralGrid"],
  roofParams: PanelPickOverlayProps["roofParams"],
): BracingPanel | null {
  if (userData?.viewportPickRole !== VIEWPORT_PICK_ROLE.WALL_PANEL) {
    return null;
  }
  return bracingPanelFromPickData(userData as WallPanelPickData, grid, roofParams);
}

export function PanelPickOverlay({
  xCoordsMm,
  zCoordsMm,
  eaveHeightMm,
  roofParams,
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
      roofParams ?? null,
    );
    const roof = roofParams ? computeRoofGeometry(gridState, roofParams) : null;

    return bracingPanels.flatMap((panel): PickMeshSpec[] => {
      if (panel.kind === "long_wall") {
        const z0M = panel.z0Mm * MM_TO_M;
        const z1M = panel.z1Mm * MM_TO_M;
        const depth = Math.max(z1M - z0M, 0.4);
        return [
          {
            kind: "wall",
            key: bracingPanelKey(panel),
            panel,
            position: [panel.xMm * MM_TO_M, eaveM / 2, (z0M + z1M) / 2],
            size: [PICK_DEPTH_M, eaveM, depth],
            pickData: pickDataFromPanel(panel),
          },
        ];
      }

      if (panel.kind === "gable_wall") {
        const x0M = panel.x0Mm * MM_TO_M;
        const x1M = panel.x1Mm * MM_TO_M;
        const width = Math.max(x1M - x0M, 0.4);
        return [
          {
            kind: "wall",
            key: bracingPanelKey(panel),
            panel,
            position: [(x0M + x1M) / 2, eaveM / 2, panel.zMm * MM_TO_M],
            size: [width, eaveM, PICK_DEPTH_M],
            pickData: pickDataFromPanel(panel),
          },
        ];
      }

      if (!roof) {
        return [];
      }

      const corners = roofPanelCornersMm(panel, gridState, roof);
      const transform = roofPickTransform(corners);
      return [
        {
          kind: "roof",
          key: bracingPanelKey(panel),
          panel,
          position: transform.position,
          quaternion: transform.quaternion,
          size: transform.size,
          pickData: pickDataFromPanel(panel),
        },
      ];
    });
  }, [projectElements, structuralGrid, xCoordsMm, zCoordsMm, eaveM, roofParams]);

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
          const panel = panelFromUserData(current.userData, gridState, roofParams);
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
  }, [active, camera, gl, roofParams, scene, setHoveredWallPanel]);

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
        if (entry.kind === "roof") {
          return (
            <group key={entry.key} position={entry.position} quaternion={entry.quaternion}>
              <mesh
                userData={{
                  viewportPickRole: VIEWPORT_PICK_ROLE.WALL_PANEL,
                  ...entry.pickData,
                }}
              >
                <boxGeometry args={entry.size} />
                <meshBasicMaterial visible={false} />
              </mesh>
              {highlighted ? (
                <mesh>
                  <boxGeometry
                    args={[
                      entry.size[0] * 1.04,
                      entry.size[1] * 1.02,
                      entry.size[2] * 2.5,
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
        }

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

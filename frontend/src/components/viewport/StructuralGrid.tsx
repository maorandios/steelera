"use client";

import { Html } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

import {
  gridLineLetter,
  gridLineNumber,
} from "@/lib/structural-grid";
import { VIEWPORT_PICK_ROLE } from "@/lib/viewport-pick";
import { viewportTheme } from "@/lib/viewport-theme";
import { useProjectStore } from "@/store/project-store";

const MM_TO_M = 0.001;
const GROUND_Y = 0;

type StructuralGridProps = {
  xCoordsMm: number[];
  zCoordsMm: number[];
  extentMinX: number;
  extentMaxX: number;
  extentMinZ: number;
  extentMaxZ: number;
};

function GridLineSegment({
  x0,
  y0,
  z0,
  x1,
  y1,
  z1,
  variant = "solid",
}: {
  x0: number;
  y0: number;
  z0: number;
  x1: number;
  y1: number;
  z1: number;
  /** Z grid lines use a lighter tone to distinguish from X lines. */
  variant?: "solid" | "minor";
}) {
  const geometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(x0, y0, z0),
      new THREE.Vector3(x1, y1, z1),
    ]);
  }, [x0, y0, z0, x1, y1, z1]);

  const material = useMemo(() => {
    const color =
      variant === "minor"
        ? viewportTheme.grid.minor
        : viewportTheme.grid.primary;
    return new THREE.LineBasicMaterial({
      color,
      transparent: variant === "minor",
      opacity: variant === "minor" ? 0.9 : 1,
    });
  }, [variant]);

  const line = useMemo(
    () => new THREE.Line(geometry, material),
    [geometry, material],
  );

  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  return <primitive object={line} />;
}

function GridLabelBubble({
  position,
  label,
}: {
  position: [number, number, number];
  label: string;
}) {
  return (
    <Html
      position={[position[0], position[1] + 0.12, position[2]]}
      center
      distanceFactor={14}
      zIndexRange={[40, 0]}
      style={{ pointerEvents: "none", userSelect: "none" }}
    >
      <div
        style={{
          width: 26,
          height: 26,
          borderRadius: "50%",
          background: viewportTheme.grid.labelBackground,
          border: `1.5px solid ${viewportTheme.grid.labelBorder}`,
          color: viewportTheme.grid.labelText,
          fontSize: 11,
          fontWeight: 700,
          lineHeight: "22px",
          textAlign: "center",
          fontFamily: "system-ui, sans-serif",
          boxShadow: viewportTheme.grid.labelShadow,
        }}
      >
        {label}
      </div>
    </Html>
  );
}

export function StructuralGrid({
  xCoordsMm,
  zCoordsMm,
  extentMinX,
  extentMaxX,
  extentMinZ,
  extentMaxZ,
}: StructuralGridProps) {
  const gridPickMode = useProjectStore((s) => s.viewportMode === "pick_grid");
  const xCoordsM = useMemo(
    () => xCoordsMm.map((value) => value * MM_TO_M),
    [xCoordsMm],
  );
  const zCoordsM = useMemo(
    () => zCoordsMm.map((value) => value * MM_TO_M),
    [zCoordsMm],
  );

  const xMin = Math.min(extentMinX, xCoordsM[0] ?? 0);
  const xMax = Math.max(extentMaxX, xCoordsM[xCoordsM.length - 1] ?? 0);
  const zMin = Math.min(extentMinZ, zCoordsM[0] ?? 0);
  const zMax = Math.max(extentMaxZ, zCoordsM[zCoordsM.length - 1] ?? 0);

  const padM = 1.5;
  const lineX0 = xMin - padM;
  const lineX1 = xMax + padM;
  const lineZ0 = zMin - padM;
  const lineZ1 = zMax + padM;

  const pickPlaneSize = Math.max(lineX1 - lineX0, lineZ1 - lineZ0, 10);

  return (
    <group>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[(lineX0 + lineX1) / 2, GROUND_Y, (lineZ0 + lineZ1) / 2]}
        userData={{ viewportPickRole: VIEWPORT_PICK_ROLE.BACKGROUND }}
      >
        <planeGeometry args={[pickPlaneSize, pickPlaneSize]} />
        <meshBasicMaterial visible={false} side={THREE.DoubleSide} />
      </mesh>

      {xCoordsM.map((x, index) => (
        <group key={`grid-x-line-${index}-${x}`}>
          <GridLineSegment
            x0={x}
            y0={GROUND_Y}
            z0={lineZ0}
            x1={x}
            y1={GROUND_Y}
            z1={lineZ1}
          />
          <GridLabelBubble
            position={[x, GROUND_Y, lineZ0]}
            label={gridLineLetter(index)}
          />
          <GridLabelBubble
            position={[x, GROUND_Y, lineZ1]}
            label={gridLineLetter(index)}
          />
        </group>
      ))}

      {zCoordsM.map((z, index) => (
        <group key={`grid-z-line-${index}-${z}`}>
          <GridLineSegment
            x0={lineX0}
            y0={GROUND_Y}
            z0={z}
            x1={lineX1}
            y1={GROUND_Y}
            z1={z}
            variant={gridPickMode ? "solid" : "minor"}
          />
          {gridPickMode ? (
            <mesh
              position={[(lineX0 + lineX1) / 2, GROUND_Y + 0.05, z]}
              rotation={[0, 0, Math.PI / 2]}
              userData={{
                viewportPickRole: VIEWPORT_PICK_ROLE.GRID_FRAME,
                frameIndex: index,
              }}
            >
              <boxGeometry args={[lineZ1 - lineZ0, 0.15, 0.35]} />
              <meshBasicMaterial visible={false} />
            </mesh>
          ) : null}
          <GridLabelBubble
            position={[lineX0, GROUND_Y, z]}
            label={gridLineNumber(index)}
          />
          <GridLabelBubble
            position={[lineX1, GROUND_Y, z]}
            label={gridLineNumber(index)}
          />
        </group>
      ))}
    </group>
  );
}

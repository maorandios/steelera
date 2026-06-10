"use client";

import { Line } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

import { memberEndpointsMm } from "@/lib/memberFrame";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";

const MM = 0.001;

function toSceneM(x: number, y: number, z: number): [number, number, number] {
  return [x * MM, y * MM, z * MM];
}
const NODE_COLOR = "#2563eb";
const LINE_COLOR = "#64748b";
const PICKED_COLOR = "#f59e0b";
const PREVIEW_COLOR = "#22c55e";

function Centerline({ element }: { element: ProjectElementMm }) {
  const ep = memberEndpointsMm(element);
  if (!ep) return null;
  const start = new THREE.Vector3(...toSceneM(ep.start.x, ep.start.y, ep.start.z));
  const end = new THREE.Vector3(...toSceneM(ep.end.x, ep.end.y, ep.end.z));
  return (
    <Line
      points={[start, end]}
      color={LINE_COLOR}
      lineWidth={1.5}
      transparent
      opacity={0.9}
    />
  );
}

function SnapNodeSphere({
  x,
  y,
  z,
  picked,
  onPick,
}: {
  x: number;
  y: number;
  z: number;
  picked: boolean;
  onPick: () => void;
}) {
  const pos = toSceneM(x, y, z);
  return (
    <mesh
      position={pos}
      onClick={(e) => {
        e.stopPropagation();
        onPick();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        document.body.style.cursor = "crosshair";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
    >
      <sphereGeometry args={[picked ? 0.22 : 0.16, 16, 16]} />
      <meshBasicMaterial
        color={picked ? PICKED_COLOR : NODE_COLOR}
        transparent
        opacity={picked ? 1 : 0.92}
      />
    </mesh>
  );
}

export function SchematicOverlay({
  projectElements,
}: {
  projectElements: ProjectElementMm[];
}) {
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const snapNodes = useProjectStore((s) => s.snapNodes);
  const pickedNodes = useProjectStore((s) => s.pickedNodes);
  const pickSnapNode = useProjectStore((s) => s.pickSnapNode);

  const pickedKeys = useMemo(
    () => new Set(pickedNodes.map((n) => `${n.x},${n.y},${n.z}`)),
    [pickedNodes],
  );

  const previewSegments = useMemo(() => {
    if (pickedNodes.length < 1) return [];
    const segs: THREE.Vector3[][] = [];
    for (let i = 0; i < pickedNodes.length - 1; i += 1) {
      const a = pickedNodes[i];
      const b = pickedNodes[i + 1];
      segs.push([
        new THREE.Vector3(...toSceneM(a.x, a.y, a.z)),
        new THREE.Vector3(...toSceneM(b.x, b.y, b.z)),
      ]);
    }
    return segs;
  }, [pickedNodes]);

  if (viewportMode !== "pick_nodes") return null;

  return (
    <group>
      {projectElements.map((el) => (
        <Centerline key={`cl-${el.id}`} element={el} />
      ))}
      {snapNodes.map((node) => {
        const key = `${node.x},${node.y},${node.z}`;
        return (
          <SnapNodeSphere
            key={node.id}
            x={node.x}
            y={node.y}
            z={node.z}
            picked={pickedKeys.has(key)}
            onPick={() => pickSnapNode(node)}
          />
        );
      })}
      {previewSegments.map((pts, i) => (
        <Line
          key={`preview-${i}`}
          points={pts}
          color={PREVIEW_COLOR}
          lineWidth={2}
        />
      ))}
    </group>
  );
}

"use client";

import { Line } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

import { memberEndpointsMm } from "@/lib/memberFrame";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";
import type { EnrichedSnapNode } from "@/types/sketch";

const MM = 0.001;
const PRIMARY_COLOR = "#2563eb";
const SECONDARY_COLOR = "#22c55e";
const PICKED_COLOR = "#f59e0b";
const LINE_COLOR = "#64748b";
const LOCKED_COLOR = "#f97316";

function toSceneM(x: number, y: number, z: number): [number, number, number] {
  return [x * MM, y * MM, z * MM];
}

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
      opacity={0.85}
    />
  );
}

function SketchNodeSphere({
  node,
  picked,
  onPick,
}: {
  node: EnrichedSnapNode;
  picked: boolean;
  onPick: () => void;
}) {
  const isPrimary = node.tier === "primary";
  const baseColor = isPrimary ? PRIMARY_COLOR : SECONDARY_COLOR;
  const color = picked ? PICKED_COLOR : baseColor;
  const radius = picked ? 0.26 : isPrimary ? 0.2 : 0.16;

  return (
    <mesh
      position={toSceneM(node.x, node.y, node.z)}
      userData={{ sketchNodeId: node.id }}
      onClick={(e) => {
        e.stopPropagation();
        onPick();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
    >
      <sphereGeometry args={[radius, 16, 16]} />
      <meshBasicMaterial color={color} transparent opacity={0.95} depthTest={false} />
    </mesh>
  );
}

export function SketchOverlay({
  projectElements,
}: {
  projectElements: ProjectElementMm[];
}) {
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const sketchSnapNodes = useProjectStore((s) => s.sketchSnapNodes);
  const sketchSession = useProjectStore((s) => s.sketchSession);
  const pickSketchNode = useProjectStore((s) => s.pickSketchNode);

  const lockedLine = useMemo(() => {
    if (!sketchSession.lockedLine) return null;
    const { start, end } = sketchSession.lockedLine;
    return [
      new THREE.Vector3(...toSceneM(start.x, start.y, start.z)),
      new THREE.Vector3(...toSceneM(end.x, end.y, end.z)),
    ];
  }, [sketchSession.lockedLine]);

  if (viewportMode !== "sketch") return null;

  return (
    <group renderOrder={10}>
      {projectElements.map((el) => (
        <Centerline key={`sk-cl-${el.id}`} element={el} />
      ))}
      {sketchSnapNodes.map((node) => (
        <SketchNodeSphere
          key={node.id}
          node={node}
          picked={node.id === sketchSession.firstNodeId}
          onPick={() => pickSketchNode(node)}
        />
      ))}
      {lockedLine ? (
        <Line points={lockedLine} color={LOCKED_COLOR} lineWidth={3} />
      ) : null}
    </group>
  );
}

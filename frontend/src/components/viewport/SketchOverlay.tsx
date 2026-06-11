"use client";

import { Line } from "@react-three/drei";
import { useMemo, useState } from "react";
import * as THREE from "three";

import {
  isSketchableElement,
  sketchMemberEndpointsMm,
} from "@/lib/sketch-nodes";
import { useProjectStore } from "@/store/project-store";
import type { ProjectElementMm } from "@/types/project";
import type { EnrichedSnapNode } from "@/types/sketch";

const MM = 0.001;
const NODE_COLOR = "#3b82f6";
const NODE_HOVER = "#60a5fa";
const PICKED_COLOR = "#f59e0b";
const LOCKED_COLOR = "#f97316";
const LINE_COLOR = "#64748b";

/** Context lines for bracing, purlins, girts, etc. */
const CONTEXT_WIREFRAME_OPACITY = 0.12;
/** Stronger lines on members you can snap to. */
const SKETCHABLE_WIREFRAME_OPACITY = 0.35;

const NODE_VISUAL_M = 0.065;
const PICKED_VISUAL_M = 0.08;
const PICK_RADIUS_M = 0.11;

function toSceneM(x: number, y: number, z: number): [number, number, number] {
  return [x * MM, y * MM, z * MM];
}

function Centerline({
  element,
  opacity,
  lineWidth = 1,
}: {
  element: ProjectElementMm;
  opacity: number;
  lineWidth?: number;
}) {
  const ep = sketchMemberEndpointsMm(element);
  if (!ep) return null;
  const start = new THREE.Vector3(
    ...toSceneM(ep.start.x, ep.start.y, ep.start.z),
  );
  const end = new THREE.Vector3(...toSceneM(ep.end.x, ep.end.y, ep.end.z));
  return (
    <Line
      points={[start, end]}
      color={LINE_COLOR}
      lineWidth={lineWidth}
      transparent
      opacity={opacity}
      depthWrite={false}
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
  const [hovered, setHovered] = useState(false);
  const color = picked ? PICKED_COLOR : hovered ? NODE_HOVER : NODE_COLOR;
  const visualRadius = picked ? PICKED_VISUAL_M : NODE_VISUAL_M;

  return (
    <group position={toSceneM(node.x, node.y, node.z)}>
      <mesh
        userData={{ sketchNodeId: node.id }}
        onClick={(e) => {
          e.stopPropagation();
          onPick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "";
        }}
      >
        <sphereGeometry args={[PICK_RADIUS_M, 12, 12]} />
        <meshBasicMaterial visible={false} />
      </mesh>

      <mesh renderOrder={50}>
        <sphereGeometry args={[visualRadius, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={picked ? 1 : hovered ? 0.98 : 0.95}
          depthTest={false}
          depthWrite={false}
        />
      </mesh>

      {picked ? (
        <mesh renderOrder={49}>
          <sphereGeometry args={[visualRadius * 1.5, 16, 16]} />
          <meshBasicMaterial
            color={PICKED_COLOR}
            transparent
            opacity={0.25}
            depthWrite={false}
          />
        </mesh>
      ) : null}
    </group>
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

  const { contextElements, sketchableElements } = useMemo(() => {
    const context: ProjectElementMm[] = [];
    const sketchable: ProjectElementMm[] = [];
    for (const el of projectElements) {
      if (!sketchMemberEndpointsMm(el)) continue;
      if (isSketchableElement(el)) sketchable.push(el);
      else context.push(el);
    }
    return { contextElements: context, sketchableElements: sketchable };
  }, [projectElements]);

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
      {contextElements.map((el) => (
        <Centerline
          key={`sk-ctx-${el.id}`}
          element={el}
          opacity={CONTEXT_WIREFRAME_OPACITY}
        />
      ))}
      {sketchableElements.map((el) => (
        <Centerline
          key={`sk-cl-${el.id}`}
          element={el}
          opacity={SKETCHABLE_WIREFRAME_OPACITY}
          lineWidth={1.25}
        />
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
        <Line
          points={lockedLine}
          color={LOCKED_COLOR}
          lineWidth={2.5}
          depthWrite={false}
        />
      ) : null}
    </group>
  );
}

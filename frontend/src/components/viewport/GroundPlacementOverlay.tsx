"use client";

import { useProjectStore } from "@/store/project-store";
import type { GroundPlacementNode } from "@/types/grid-selection";

const MM = 0.001;
const NODE_COLOR = "#16a34a";
const TRUSS_COLOR = "#0d9488";
const OFFSET_COLOR = "#ca8a04";
const MID_COLOR = "#2563eb";

function colorForKind(kind: string): string {
  if (kind === "truss_panel") return TRUSS_COLOR;
  if (kind === "wall_offset") return OFFSET_COLOR;
  if (kind === "mid_bay") return MID_COLOR;
  return NODE_COLOR;
}

function GroundDot({
  node,
  onPick,
}: {
  node: GroundPlacementNode;
  onPick: () => void;
}) {
  const color = colorForKind(node.kind);
  return (
    <mesh
      position={[node.x * MM, node.y * MM + 0.04, node.z * MM]}
      userData={{ groundPlacementNodeId: node.id }}
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
      <sphereGeometry args={[node.kind === "wall_offset" ? 0.2 : 0.14, 14, 14]} />
      <meshBasicMaterial color={color} transparent opacity={0.95} />
    </mesh>
  );
}

export function GroundPlacementOverlay() {
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const groundNodes = useProjectStore((s) => s.groundPlacementNodes);
  const pickGroundNode = useProjectStore((s) => s.pickGroundPlacementNode);

  if (viewportMode !== "pick_column_nodes") {
    return null;
  }

  return (
    <group>
      {groundNodes.map((node) => (
        <GroundDot
          key={node.id}
          node={node}
          onPick={() => void pickGroundNode(node)}
        />
      ))}
    </group>
  );
}

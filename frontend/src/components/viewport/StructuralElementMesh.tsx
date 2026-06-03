"use client";

import type { StructuralElement } from "@/types/project";

interface StructuralElementMeshProps {
  element: StructuralElement;
}

function elementColor(element: StructuralElement): string {
  if (element.color) return element.color;
  switch (element.shape_type) {
    case "I-beam":
      return "#94a3b8";
    case "C-channel":
      return "#64748b";
    case "Box":
      return "#71717a";
    case "Pipe":
      return "#a1a1aa";
    default:
      return "#71717a";
  }
}

export function StructuralElementMesh({ element }: StructuralElementMeshProps) {
  const color = elementColor(element);
  const [px, py, pz] = element.position;
  const [rx, ry, rz] = element.rotation;
  const [sx, sy, sz] = element.size;

  return (
    <mesh position={[px, pz, py]} rotation={[rx, rz, ry]}>
      <boxGeometry args={[sx, sz, sy]} />
      <meshStandardMaterial color={color} metalness={0.35} roughness={0.55} />
    </mesh>
  );
}

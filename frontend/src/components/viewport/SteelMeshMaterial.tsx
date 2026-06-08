"use client";

import type { MeshStandardMaterialParameters } from "three";

import { viewportTheme } from "@/lib/viewport-theme";

type SteelMeshMaterialProps = MeshStandardMaterialParameters & {
  metalness?: number;
  roughness?: number;
};

export function SteelMeshMaterial({
  metalness = viewportTheme.steel.metalness,
  roughness = viewportTheme.steel.roughness,
  ...props
}: SteelMeshMaterialProps) {
  return (
    <meshStandardMaterial
      metalness={metalness}
      roughness={roughness}
      {...props}
    />
  );
}

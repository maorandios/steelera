"use client";

import { Edges } from "@react-three/drei";

import { viewportTheme } from "@/lib/viewport-theme";

export function MeshSchematicEdges() {
  return <Edges color={viewportTheme.steel.outline} threshold={8} />;
}

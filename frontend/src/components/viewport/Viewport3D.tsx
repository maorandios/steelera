"use client";

import dynamic from "next/dynamic";

import { PropertiesPanel } from "@/components/properties/PropertiesPanel";
import { SceneContent } from "@/components/viewport/SceneContent";
import { useProjectStore } from "@/store/project-store";

const Canvas = dynamic(
  () => import("@react-three/fiber").then((mod) => mod.Canvas),
  { ssr: false },
);

export function Viewport3D() {
  const projectElements = useProjectStore((state) => state.projectElements);
  const clearSelection = useProjectStore((state) => state.clearSelection);
  const count = projectElements.length;

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden rounded-xl border border-border bg-[#0c0c0e]">
      <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-md border border-border/80 bg-background/80 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground backdrop-blur-sm">
        {count > 0
          ? `${count} element${count > 1 ? "s" : ""}${
              projectElements[0]?.profile_name
                ? ` · ${projectElements[0].profile_name}`
                : ""
            }`
          : "3D viewport — awaiting structure"}
      </div>
      <PropertiesPanel />
      <Canvas
        className="h-full w-full touch-none"
        gl={{ antialias: true }}
        onPointerMissed={() => clearSelection()}
      >
        <color attach="background" args={["#0c0c0e"]} />
        <SceneContent projectElements={projectElements} />
      </Canvas>
    </div>
  );
}

"use client";

import dynamic from "next/dynamic";

import { SceneContent } from "@/components/viewport/SceneContent";
import { useProjectStore } from "@/store/project-store";

const Canvas = dynamic(
  () => import("@react-three/fiber").then((mod) => mod.Canvas),
  { ssr: false },
);

export function Viewport3D() {
  const projectState = useProjectStore((s) => s.projectState);
  const count = projectState.elements.length;

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden rounded-xl border border-border bg-[#0c0c0e]">
      <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-md border border-border/80 bg-background/80 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground backdrop-blur-sm">
        {count > 0
          ? `${count} elements`
          : "3D viewport — awaiting structure"}
      </div>
      <Canvas
        className="h-full w-full touch-none"
        gl={{ antialias: true, alpha: false }}
        dpr={[1, 2]}
      >
        <color attach="background" args={["#0c0c0e"]} />
        <SceneContent projectState={projectState} />
      </Canvas>
    </div>
  );
}

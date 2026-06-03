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
      <div className="pointer-events-none absolute bottom-3 right-3 z-10 rounded-md border border-border/80 bg-background/85 px-2.5 py-2 backdrop-blur-sm">
        <svg
          viewBox="0 0 64 64"
          className="h-14 w-14"
          aria-label="World axes: X right, Y up, Z forward"
        >
          <line x1="12" y1="52" x2="52" y2="52" stroke="#f87171" strokeWidth="2.5" />
          <polygon points="52,52 46,49 46,55" fill="#f87171" />
          <text x="54" y="56" fill="#f87171" fontSize="9" fontWeight="600">
            X
          </text>
          <line x1="12" y1="52" x2="12" y2="12" stroke="#4ade80" strokeWidth="2.5" />
          <polygon points="12,12 9,18 15,18" fill="#4ade80" />
          <text x="4" y="10" fill="#4ade80" fontSize="9" fontWeight="600">
            Y
          </text>
          <line x1="12" y1="52" x2="32" y2="32" stroke="#60a5fa" strokeWidth="2.5" />
          <polygon points="32,32 27,34 29,38" fill="#60a5fa" />
          <text x="34" y="30" fill="#60a5fa" fontSize="9" fontWeight="600">
            Z
          </text>
        </svg>
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

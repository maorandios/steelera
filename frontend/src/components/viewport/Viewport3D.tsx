"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import * as THREE from "three";

import { SceneContent } from "@/components/viewport/SceneContent";
import { useProjectStore } from "@/store/project-store";

const Canvas = dynamic(
  () => import("@react-three/fiber").then((mod) => mod.Canvas),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 flex items-center justify-center bg-[#0c0c0e] text-xs text-muted-foreground">
        Loading 3D…
      </div>
    ),
  },
);

export function Viewport3D() {
  const projectElements = useProjectStore((state) => state.projectElements);
  const clearSelection = useProjectStore((state) => state.clearSelection);
  const count = projectElements.length;
  const [canvasKey, setCanvasKey] = useState(0);
  const [webglLost, setWebglLost] = useState(false);

  const remountCanvas = useCallback(() => {
    setWebglLost(false);
    setCanvasKey((key) => key + 1);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden rounded-xl border border-border bg-[#0c0c0e]">
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
      {webglLost && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-[#0c0c0e]/95 px-6 text-center">
          <p className="text-sm text-muted-foreground">
            The 3D graphics context was lost (often caused by GPU memory pressure).
          </p>
          <button
            type="button"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            onClick={remountCanvas}
          >
            Restore 3D view
          </button>
        </div>
      )}
      <Canvas
        key={canvasKey}
        className="!h-full !w-full touch-none"
        style={{ width: "100%", height: "100%", background: "#0c0c0e" }}
        dpr={[1, 1.5]}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
          preserveDrawingBuffer: false,
        }}
        onCreated={({ gl, scene }) => {
          const bg = new THREE.Color("#0c0c0e");
          scene.background = bg;
          gl.setClearColor(bg, 1);
          const canvas = gl.domElement;
          const onLost = (event: Event) => {
            event.preventDefault();
            setWebglLost(true);
          };
          const onRestored = () => {
            gl.resetState();
            setWebglLost(false);
          };
          canvas.addEventListener("webglcontextlost", onLost);
          canvas.addEventListener("webglcontextrestored", onRestored);
        }}
        onPointerMissed={() => clearSelection()}
      >
        <SceneContent projectElements={projectElements} />
      </Canvas>
    </div>
  );
}

"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import * as THREE from "three";

import { CanvasErrorBoundary } from "@/components/viewport/CanvasErrorBoundary";
import { SceneContent } from "@/components/viewport/SceneContent";
import { WebGLContextGuard } from "@/components/viewport/WebGLContextGuard";
import { viewportTheme } from "@/lib/viewport-theme";
import { useProjectStore } from "@/store/project-store";

const Canvas = dynamic(
  () => import("@react-three/fiber").then((mod) => mod.Canvas),
  {
    ssr: false,
    loading: () => (
      <div
        className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground"
        style={{ background: viewportTheme.canvas.background }}
      >
        Loading 3D…
      </div>
    ),
  },
);

export function Viewport3D() {
  const projectElements = useProjectStore((state) => state.projectElements);
  const count = projectElements.length;
  const [canvasKey, setCanvasKey] = useState(0);
  const [webglLost, setWebglLost] = useState(false);
  const { background, overlay, border } = viewportTheme.canvas;
  const { maxDpr } = viewportTheme.performance;

  const remountCanvas = useCallback(() => {
    setWebglLost(false);
    setCanvasKey((key) => key + 1);
  }, []);

  const handleContextLost = useCallback(() => setWebglLost(true), []);
  const handleContextRestored = useCallback(() => setWebglLost(false), []);

  return (
    <div
      className="absolute inset-0 overflow-hidden rounded-xl border bg-white shadow-sm"
      style={{ borderColor: border, background }}
    >
      <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-md border border-slate-200 bg-white/90 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider text-slate-600 shadow-sm backdrop-blur-sm">
        {count > 0
          ? `${count} element${count > 1 ? "s" : ""}${
              projectElements[0]?.profile_name
                ? ` · ${projectElements[0].profile_name}`
                : ""
            }`
          : "3D viewport — awaiting structure"}
      </div>
      <div className="pointer-events-none absolute bottom-3 right-3 z-10 rounded-md border border-slate-200 bg-white/90 px-2.5 py-2 shadow-sm backdrop-blur-sm">
        <svg
          viewBox="0 0 64 64"
          className="h-14 w-14"
          aria-label="World axes: X right, Y up, Z forward"
        >
          <line x1="12" y1="52" x2="52" y2="52" stroke="#ef4444" strokeWidth="2.5" />
          <polygon points="52,52 46,49 46,55" fill="#ef4444" />
          <text x="54" y="56" fill="#ef4444" fontSize="9" fontWeight="600">
            X
          </text>
          <line x1="12" y1="52" x2="12" y2="12" stroke="#16a34a" strokeWidth="2.5" />
          <polygon points="12,12 9,18 15,18" fill="#16a34a" />
          <text x="4" y="10" fill="#16a34a" fontSize="9" fontWeight="600">
            Y
          </text>
          <line x1="12" y1="52" x2="32" y2="32" stroke="#2563eb" strokeWidth="2.5" />
          <polygon points="32,32 27,34 29,38" fill="#2563eb" />
          <text x="34" y="30" fill="#2563eb" fontSize="9" fontWeight="600">
            Z
          </text>
        </svg>
      </div>
      {webglLost && (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 px-6 text-center"
          style={{ background: overlay }}
        >
          <p className="text-sm text-slate-600">
            The 3D graphics context was lost (often caused by GPU memory pressure).
          </p>
          <button
            type="button"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            onClick={remountCanvas}
          >
            Restore 3D view
          </button>
        </div>
      )}
      <CanvasErrorBoundary key={`boundary-${canvasKey}`} onReset={remountCanvas}>
        <Canvas
          key={canvasKey}
          className="!h-full !w-full touch-none"
          style={{ width: "100%", height: "100%", background }}
          dpr={[1, maxDpr]}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: "default",
            preserveDrawingBuffer: false,
          }}
          onCreated={({ gl, scene }) => {
            const bg = new THREE.Color(background);
            scene.background = bg;
            gl.setClearColor(bg, 1);
          }}
        >
          <WebGLContextGuard
            onLost={handleContextLost}
            onRestored={handleContextRestored}
          />
          <SceneContent projectElements={projectElements} />
        </Canvas>
      </CanvasErrorBoundary>
    </div>
  );
}

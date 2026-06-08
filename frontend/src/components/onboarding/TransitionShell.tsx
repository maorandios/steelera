"use client";

import { useEffect } from "react";

import { WizardBackground } from "@/components/onboarding/WizardBackground";
import { Viewport3D } from "@/components/viewport/Viewport3D";
import { useProjectStore } from "@/store/project-store";

export function TransitionShell() {
  const completeTransition = useProjectStore((s) => s.completeTransition);
  const statuses = useProjectStore((s) => s.statuses);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);

  useEffect(() => {
    if (!isMacroLoading) {
      const t = window.setTimeout(() => completeTransition(), 900);
      return () => window.clearTimeout(t);
    }
  }, [isMacroLoading, completeTransition]);

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      <WizardBackground sharp />
      <div className="absolute inset-0 p-4 pt-16 opacity-100 transition-opacity duration-700">
        <div className="h-full w-full">
          <Viewport3D />
        </div>
      </div>
      <div
        className="pointer-events-none absolute inset-0 flex items-center justify-center bg-white/20 transition-opacity duration-500"
        aria-live="polite"
      >
        <div
          className="rounded-2xl border border-white/60 px-8 py-6 text-center shadow-xl"
          style={{
            background: "rgba(255, 255, 255, 0.85)",
            backdropFilter: "blur(16px)",
          }}
        >
          <p className="text-sm font-medium text-slate-800">
            Bringing your structure to life…
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {statuses[statuses.length - 1] ?? "Generating 3D model"}
          </p>
        </div>
      </div>
    </div>
  );
}

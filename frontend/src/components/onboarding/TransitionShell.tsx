"use client";

import { useEffect } from "react";

import { OnboardingLoader } from "@/components/onboarding/OnboardingLoader";
import { onboardingTheme } from "@/lib/onboarding-theme";
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

  const status = statuses[statuses.length - 1] ?? "Generating 3D model";

  return (
    <div
      className="relative h-dvh w-full overflow-hidden"
      style={{ background: onboardingTheme.canvas }}
    >
      <div className="absolute inset-0 p-4 pt-16 opacity-100 transition-opacity duration-700">
        <div className="h-full w-full">
          <Viewport3D />
        </div>
      </div>

      <div
        className="pointer-events-none absolute inset-0 flex items-center justify-center transition-opacity duration-500"
        style={{ background: onboardingTheme.overlay }}
        aria-live="polite"
      >
        <div
          className="animate-onboarding-fade-up rounded-2xl border px-10 py-8 text-center shadow-[0_8px_40px_rgba(15,23,42,0.08)] backdrop-blur-xl"
          style={{
            background: onboardingTheme.glass,
            borderColor: onboardingTheme.glassBorder,
          }}
        >
          <OnboardingLoader
            label="Bringing your structure to life"
            sublabel={status}
          />
          <div className="mt-5 h-0.5 w-48 overflow-hidden rounded-full bg-slate-200/80">
            <div
              className="h-full w-1/3 rounded-full bg-gradient-to-r from-transparent via-slate-700 to-transparent animate-onboarding-shimmer"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

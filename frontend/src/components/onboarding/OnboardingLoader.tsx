"use client";

import { cn } from "@/lib/utils";

type OnboardingLoaderProps = {
  label?: string;
  sublabel?: string;
  className?: string;
  size?: "sm" | "md";
};

export function OnboardingLoader({
  label,
  sublabel,
  className,
  size = "md",
}: OnboardingLoaderProps) {
  const ring = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div className={cn("relative", ring)}>
        <div
          className={cn(
            "absolute inset-0 rounded-full border-2 border-slate-200/80",
          )}
        />
        <div
          className={cn(
            "absolute inset-0 rounded-full border-2 border-transparent border-t-slate-800 border-r-slate-400 animate-onboarding-orbit",
          )}
        />
        <div className="absolute inset-[30%] rounded-full bg-slate-800/90" />
      </div>
      {label ? (
        <div className="text-center">
          <p className="text-sm font-medium tracking-tight text-slate-800">{label}</p>
          {sublabel ? (
            <p className="mt-1 text-xs text-slate-500">{sublabel}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

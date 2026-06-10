"use client";

import { cn } from "@/lib/utils";

type WizardBackgroundProps = {
  minimal?: boolean;
  sharp?: boolean;
};

export function WizardBackground({ minimal = false, sharp = false }: WizardBackgroundProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden transition-[filter,opacity] duration-700 ease-out",
        minimal ? "opacity-100" : "opacity-90",
      )}
      style={{ filter: sharp ? "none" : undefined }}
      aria-hidden
    >
      <div
        className={cn(
          "absolute inset-0",
          minimal ? "" : "animate-gradient-shift",
        )}
        style={{
          background: minimal
            ? "linear-gradient(165deg, #f8fafc 0%, #f1f5f9 35%, #eef2ff 70%, #f8fafc 100%)"
            : "linear-gradient(135deg, #e8eef5 0%, #dce6f0 25%, #cfd9e8 50%, #e2e8f0 75%, #d4dce8 100%)",
          backgroundSize: minimal ? undefined : "400% 400%",
        }}
      />
      {minimal ? (
        <>
          <div
            className="absolute -left-24 -top-24 h-80 w-80 rounded-full opacity-40 blur-3xl"
            style={{ background: "radial-gradient(circle, #dbeafe 0%, transparent 70%)" }}
          />
          <div
            className="absolute -bottom-32 -right-16 h-96 w-96 rounded-full opacity-35 blur-3xl"
            style={{ background: "radial-gradient(circle, #e0e7ff 0%, transparent 70%)" }}
          />
        </>
      ) : (
        <div
          className="absolute left-1/2 top-1/2 h-[min(70vw,520px)] w-[min(90vw,900px)] -translate-x-1/2 -translate-y-1/2 opacity-[0.08]"
          style={{
            background:
              "repeating-linear-gradient(90deg, transparent, transparent 48px, #64748b 48px, #64748b 49px), repeating-linear-gradient(0deg, transparent, transparent 32px, #64748b 32px, #64748b 33px)",
            transform: "translate(-50%, -50%) perspective(800px) rotateX(58deg) rotateZ(-8deg)",
          }}
        />
      )}
    </div>
  );
}

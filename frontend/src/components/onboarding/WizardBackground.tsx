"use client";

import { onboardingTheme } from "@/lib/onboarding-theme";
import { cn } from "@/lib/utils";

type WizardBackgroundProps = {
  minimal?: boolean;
  sharp?: boolean;
};

export function WizardBackground({ minimal = false, sharp = false }: WizardBackgroundProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        sharp ? "opacity-100" : "opacity-95",
      )}
      style={{ background: onboardingTheme.canvas }}
      aria-hidden
    >
      {/* Engineering grid */}
      <div
        className="absolute inset-0 opacity-[0.45]"
        style={{
          backgroundImage: `
            linear-gradient(${onboardingTheme.border} 1px, transparent 1px),
            linear-gradient(90deg, ${onboardingTheme.border} 1px, transparent 1px)
          `,
          backgroundSize: minimal ? "48px 48px" : "64px 64px",
          maskImage:
            "radial-gradient(ellipse 80% 70% at 50% 45%, black 20%, transparent 75%)",
        }}
      />

      {/* Soft vignette */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 90% 80% at 50% 40%, transparent 0%, rgba(245,246,248,0.4) 55%, rgba(245,246,248,0.95) 100%)",
        }}
      />

      {!minimal ? (
        <div
          className="absolute left-1/2 top-1/2 h-[min(65vw,480px)] w-[min(88vw,820px)] -translate-x-1/2 -translate-y-1/2 opacity-[0.06]"
          style={{
            background:
              "repeating-linear-gradient(90deg, transparent, transparent 47px, #94a3b8 47px, #94a3b8 48px), repeating-linear-gradient(0deg, transparent, transparent 31px, #94a3b8 31px, #94a3b8 32px)",
            transform: "translate(-50%, -50%) perspective(900px) rotateX(58deg) rotateZ(-6deg)",
          }}
        />
      ) : null}

      {/* Ambient glow — neutral, not blue */}
      <div
        className="absolute -left-32 top-1/4 h-72 w-72 rounded-full blur-3xl"
        style={{ background: "radial-gradient(circle, rgba(148,163,184,0.18) 0%, transparent 70%)" }}
      />
      <div
        className="absolute -right-24 bottom-1/4 h-80 w-80 rounded-full blur-3xl"
        style={{ background: "radial-gradient(circle, rgba(203,213,225,0.22) 0%, transparent 70%)" }}
      />

      {/* Scan line */}
      <div className="absolute inset-x-0 top-0 h-full overflow-hidden opacity-30">
        <div
          className="animate-onboarding-scan h-24 w-full"
          style={{
            background:
              "linear-gradient(180deg, transparent, rgba(148,163,184,0.12), transparent)",
          }}
        />
      </div>
    </div>
  );
}

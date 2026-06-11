import { viewportTheme } from "@/lib/viewport-theme";

/** Onboarding surfaces share the 3D viewport canvas palette. */
export const onboardingTheme = {
  canvas: viewportTheme.canvas.background,
  border: viewportTheme.canvas.border,
  overlay: viewportTheme.canvas.overlay,
  accent: "#0f172a",
  accentSoft: "#334155",
  muted: "#64748b",
  glass: "rgba(255, 255, 255, 0.78)",
  glassBorder: "rgba(226, 232, 240, 0.95)",
  glassShadow: "0 8px 40px rgba(15, 23, 42, 0.06)",
  focusRing: "rgba(15, 23, 42, 0.08)",
} as const;

"use client";

import { OnboardingShell } from "@/components/onboarding/OnboardingShell";
import { TransitionShell } from "@/components/onboarding/TransitionShell";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { useProjectStore } from "@/store/project-store";

export function AppShell() {
  const uiPhase = useProjectStore((s) => s.uiPhase);

  if (uiPhase === "onboarding") {
    return <OnboardingShell />;
  }
  if (uiPhase === "transition") {
    return <TransitionShell />;
  }
  return <WorkspaceLayout />;
}

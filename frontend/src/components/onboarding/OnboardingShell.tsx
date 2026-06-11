"use client";

import { OnboardingStartScreen } from "@/components/onboarding/OnboardingStartScreen";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { WizardBackground } from "@/components/onboarding/WizardBackground";
import { isOnboardingStartScreen } from "@/lib/onboarding-flow";
import { useProjectStore } from "@/store/project-store";

export function OnboardingShell() {
  const showStart = useProjectStore((s) =>
    isOnboardingStartScreen({
      onboardingPhase: s.onboardingPhase,
      onboardingAwaitingCustom: s.onboardingAwaitingCustom,
      isProposing: s.isProposing,
      messages: s.messages,
    }),
  );

  return (
    <div className="relative flex h-dvh w-full flex-col overflow-hidden">
      <WizardBackground minimal />
      <div className="relative z-10 min-h-0 flex-1 overflow-y-auto">
        {showStart ? <OnboardingStartScreen /> : <OnboardingWizard />}
      </div>
    </div>
  );
}

"use client";

import { useProjectStore } from "@/store/project-store";

import { EngineeringProposalPanel } from "@/components/onboarding/EngineeringProposalPanel";
import { WizardBackground } from "@/components/onboarding/WizardBackground";
import { WizardStep1Form } from "@/components/onboarding/WizardStep1Form";
import { WizardStep2Form } from "@/components/onboarding/WizardStep2Form";

export function OnboardingShell() {
  const messages = useProjectStore((s) => s.messages);
  const wizardStep = useProjectStore((s) => s.wizardStep);
  const wizardStep1 = useProjectStore((s) => s.wizardStep1);
  const wizardStep2 = useProjectStore((s) => s.wizardStep2);
  const proposal = useProjectStore((s) => s.proposal);
  const proposalDraft = useProjectStore((s) => s.proposalDraft);
  const isProposing = useProjectStore((s) => s.isProposing);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const submitWizardStep1 = useProjectStore((s) => s.submitWizardStep1);
  const submitWizardStep2 = useProjectStore((s) => s.submitWizardStep2);
  const wizardBack = useProjectStore((s) => s.wizardBack);
  const updateProposalDraft = useProjectStore((s) => s.updateProposalDraft);
  const buildFromProposal = useProjectStore((s) => s.buildFromProposal);

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="relative flex h-dvh w-full items-center justify-center overflow-hidden">
      <WizardBackground />
      <div
        className="relative z-10 mx-4 w-full max-w-lg rounded-2xl border border-white/50 shadow-2xl"
        style={{
          background: "rgba(255, 255, 255, 0.72)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
      >
        <div className="border-b border-white/40 px-6 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Steelera
          </p>
          <h1 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
            Structural design co-pilot
          </h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Step {wizardStep} of 3 ·{" "}
            {wizardStep === 1
              ? "Dimensions"
              : wizardStep === 2
                ? "Roof & site"
                : "Review & build"}
          </p>
        </div>

        <div className="max-h-[min(70vh,640px)] overflow-y-auto px-6 py-4">
          {lastAssistant ? (
            <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">
              {lastAssistant.content}
            </p>
          ) : null}

          {wizardStep === 1 ? (
            <WizardStep1Form
              initial={wizardStep1}
              disabled={isProposing || isMacroLoading}
              onSubmit={submitWizardStep1}
            />
          ) : null}

          {wizardStep === 2 ? (
            <WizardStep2Form
              initial={wizardStep2}
              disabled={isProposing || isMacroLoading}
              loading={isProposing}
              onBack={() => wizardBack(1)}
              onSubmit={submitWizardStep2}
            />
          ) : null}

          {wizardStep === 3 && proposal && proposalDraft ? (
            <EngineeringProposalPanel
              proposal={proposal}
              draft={proposalDraft}
              disabled={isMacroLoading}
              building={isMacroLoading}
              onChange={updateProposalDraft}
              onBack={() => wizardBack(2)}
              onBuild={buildFromProposal}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

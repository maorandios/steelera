"use client";

import { ChevronDown } from "lucide-react";

import { ProposalSectionPicker } from "@/components/chat/ProposalSectionPicker";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { onboardingTheme } from "@/lib/onboarding-theme";
import { PROPOSAL_DISCLAIMER_SHORT } from "@/lib/proposal-copy";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";

type ChatProposalBlockProps = {
  active: boolean;
  variant?: "default" | "wizard";
};

function ToggleRow({
  id,
  label,
  checked,
  disabled,
  onCheckedChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <Label htmlFor={id} className="text-sm text-slate-600">
        {label}
      </Label>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
      />
    </div>
  );
}

function parseSummaryParts(summary: string): string[] {
  return summary.split("·").map((part) => part.trim()).filter(Boolean);
}

export function ChatProposalBlock({
  active,
  variant = "default",
}: ChatProposalBlockProps) {
  const wizard = variant === "wizard";
  const proposal = useProjectStore((s) => s.proposal);
  const proposalDraft = useProjectStore((s) => s.proposalDraft);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const updateProposalDraft = useProjectStore((s) => s.updateProposalDraft);
  const applyProposalTier = useProjectStore((s) => s.applyProposalTier);
  const buildFromProposal = useProjectStore((s) => s.buildFromProposal);

  if (!proposal || !proposalDraft) return null;

  const disabled = !active || isMacroLoading;
  const summaryParts = parseSummaryParts(proposal.summary);

  return (
    <div className={cn("space-y-4", wizard ? "mt-0" : "mt-3")}>
      <div
        className={cn(
          wizard
            ? "rounded-2xl border bg-white/75 p-5 shadow-[0_8px_40px_rgba(15,23,42,0.06)] backdrop-blur-xl"
            : "rounded-2xl border border-primary/20 bg-primary/5 p-4",
        )}
        style={wizard ? { borderColor: onboardingTheme.glassBorder } : undefined}
      >
        {!wizard ? (
          <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
            Your model
          </p>
        ) : (
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
            Model summary
          </p>
        )}

        {wizard && summaryParts.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {summaryParts.map((part) => (
              <span
                key={part}
                className="inline-flex items-center rounded-full border border-slate-200/80 bg-slate-50 px-3 py-1 text-sm font-medium text-slate-700"
              >
                {part}
              </span>
            ))}
          </div>
        ) : (
          <p
            className={cn(
              "font-medium text-slate-800",
              wizard ? "mt-3 text-base" : "mt-1 text-sm",
            )}
          >
            {proposal.summary}
          </p>
        )}

        <p
          className={cn(
            "text-slate-500",
            wizard ? "mt-4 text-xs leading-relaxed" : "mt-2 text-[10px] text-muted-foreground",
          )}
        >
          {PROPOSAL_DISCLAIMER_SHORT}
        </p>
      </div>

      <ProposalSectionPicker
        proposal={proposal}
        draft={proposalDraft}
        disabled={disabled}
        building={isMacroLoading}
        variant={variant}
        onApplyTier={applyProposalTier}
        onFieldChange={updateProposalDraft}
        onBuild={buildFromProposal}
      />

      <details
        className={cn(
          "group rounded-2xl border",
          wizard
            ? "border-slate-200/80 bg-white/60 shadow-sm backdrop-blur-sm"
            : "border-border/60 bg-muted/10",
        )}
        style={wizard ? { borderColor: onboardingTheme.glassBorder } : undefined}
      >
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3.5 text-sm font-medium text-slate-600 marker:content-none hover:text-slate-900">
          Layout options
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-180" />
        </summary>
        <div className="divide-y divide-slate-100 border-t border-slate-100 px-4">
          <ToggleRow
            id="prop-truss"
            label="Roof truss"
            checked={Boolean(proposalDraft.use_truss)}
            disabled={disabled}
            onCheckedChange={(v) =>
              updateProposalDraft({ use_truss: v, truss_type: v ? "pratt" : "none" })
            }
          />
          <ToggleRow
            id="prop-x"
            label="Wall X-bracing"
            checked={Boolean(proposalDraft.x_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => updateProposalDraft({ x_bracing: v })}
          />
          <ToggleRow
            id="prop-roof-x"
            label="Roof X-bracing"
            checked={Boolean(proposalDraft.roof_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => updateProposalDraft({ roof_bracing: v })}
          />
          <ToggleRow
            id="prop-gable-x"
            label="Gable X-bracing"
            checked={Boolean(proposalDraft.gable_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => updateProposalDraft({ gable_bracing: v })}
          />
          <ToggleRow
            id="prop-sag"
            label="Anti-sag rods"
            checked={Boolean(proposalDraft.sag_rods)}
            disabled={disabled}
            onCheckedChange={(v) => updateProposalDraft({ sag_rods: v })}
          />
          <ToggleRow
            id="prop-girts"
            label="Wall girts"
            checked={proposalDraft.generate_wall_girts !== false}
            disabled={disabled}
            onCheckedChange={(v) => updateProposalDraft({ generate_wall_girts: v })}
          />
        </div>
      </details>
    </div>
  );
}

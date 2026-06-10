"use client";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ProposalSectionPicker } from "@/components/chat/ProposalSectionPicker";
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
    <div className="flex items-center justify-between gap-3 py-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
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

  return (
    <div className={cn("space-y-3", wizard ? "mt-0" : "mt-3")}>
      <div
        className={cn(
          "rounded-2xl p-4",
          wizard
            ? "border border-white/80 bg-white/70 shadow-sm backdrop-blur-sm"
            : "border border-primary/20 bg-primary/5",
        )}
      >
        {!wizard ? (
          <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
            Your model
          </p>
        ) : null}
        <p
          className={cn(
            "font-medium text-slate-800",
            wizard ? "text-base" : "mt-1 text-sm",
          )}
        >
          {proposal.summary}
        </p>
        <p
          className={cn(
            "mt-2 text-slate-500",
            wizard ? "text-xs" : "text-[10px] text-muted-foreground",
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
        onApplyTier={applyProposalTier}
        onFieldChange={updateProposalDraft}
        onBuild={buildFromProposal}
      />

      <details
        className={cn(
          "rounded-2xl px-3 py-2 text-xs",
          wizard
            ? "border border-white/80 bg-white/50 shadow-sm"
            : "border border-border/60 bg-muted/10",
        )}
      >
        <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
          Layout options
        </summary>
        <div className="mt-1 divide-y divide-border/60">
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

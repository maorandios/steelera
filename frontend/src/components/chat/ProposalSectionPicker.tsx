"use client";

import { Loader2, Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { activeTierFromDraft, tierLabel } from "@/lib/proposal-tier";
import type { GridDefinition } from "@/types/spatial-grid";
import type { SectionTierName, SectionTierPackage, ShedProposalResult } from "@/types/wizard";

type ProposalSectionPickerProps = {
  proposal: ShedProposalResult;
  draft: GridDefinition;
  disabled?: boolean;
  building?: boolean;
  onApplyTier: (tier: SectionTierName) => void;
  onFieldChange: (patch: Partial<GridDefinition>) => void;
  onBuild: () => void;
};

function uniqueOptions(
  tiers: SectionTierPackage[],
  key: keyof SectionTierPackage,
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of tiers) {
    const v = t[key];
    if (typeof v === "string" && v && !seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

export function ProposalSectionPicker({
  proposal,
  draft,
  disabled,
  building,
  onApplyTier,
  onFieldChange,
  onBuild,
}: ProposalSectionPickerProps) {
  const tiers = proposal.section_tiers ?? [];
  const active = activeTierFromDraft(tiers, draft) ?? proposal.active_tier ?? "recommended";

  if (tiers.length === 0) return null;

  const columnOptions = uniqueOptions(tiers, "column_profile");
  const chordOptions = uniqueOptions(tiers, "truss_chord_profile");
  const webOptions = uniqueOptions(tiers, "truss_web_profile");
  const tieOptions = uniqueOptions(tiers, "tie_beam_profile");
  const braceOptions = uniqueOptions(tiers, "bracing_profile");

  const showTruss = draft.use_truss !== false;

  return (
    <div className="space-y-3 rounded-xl border border-border/60 bg-muted/20 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Starting sections
      </p>

      <p className="text-xs text-muted-foreground">
        Pick a package — <span className="font-medium text-foreground">{tierLabel(active)}</span>{" "}
        is selected.
      </p>

      <div className="flex flex-wrap gap-2">
        {(["light", "recommended", "conservative"] as const).map((tier) => (
          <Button
            key={tier}
            type="button"
            size="sm"
            variant={active === tier ? "default" : "outline"}
            disabled={disabled || building}
            className={cn("h-8 text-xs", active === tier && "ring-2 ring-primary/30")}
            onClick={() => onApplyTier(tier)}
          >
            {tierLabel(tier)}
            {tier === "recommended" ? " ★" : ""}
          </Button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-md border border-border/50 bg-background/60">
        <table className="w-full min-w-[320px] text-left text-[11px]">
          <thead>
            <tr className="border-b border-border/50 text-muted-foreground">
              <th className="px-2 py-1.5 font-medium">Package</th>
              <th className="px-2 py-1.5 font-medium">Columns</th>
              {showTruss ? (
                <>
                  <th className="px-2 py-1.5 font-medium">Chords</th>
                  <th className="px-2 py-1.5 font-medium">Webs</th>
                </>
              ) : null}
              <th className="px-2 py-1.5 font-medium">Ties</th>
              <th className="px-2 py-1.5 font-medium">Bracing</th>
            </tr>
          </thead>
          <tbody>
            {tiers.map((t) => (
              <tr
                key={t.tier}
                className={cn(
                  "border-b border-border/30 last:border-0",
                  active === t.tier && "bg-primary/5",
                )}
              >
                <td className="px-2 py-1.5">{tierLabel(t.tier)}</td>
                <td className="px-2 py-1.5 font-mono">{t.column_profile}</td>
                {showTruss ? (
                  <>
                    <td className="px-2 py-1.5 font-mono">
                      {t.truss_chord_profile ?? "—"}
                    </td>
                    <td className="px-2 py-1.5 font-mono">
                      {t.truss_web_profile ?? "—"}
                    </td>
                  </>
                ) : null}
                <td className="px-2 py-1.5 font-mono">{t.tie_beam_profile ?? "IPE200"}</td>
                <td className="px-2 py-1.5 font-mono">{t.bracing_profile}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Button
        type="button"
        disabled={disabled || building}
        onClick={onBuild}
        className="w-full gap-2"
      >
        {building ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Building model…
          </>
        ) : (
          <>
            <Rocket className="h-4 w-4" />
            Build model
          </>
        )}
      </Button>

      <details className="text-xs">
        <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
          Advanced — edit sections
        </summary>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <FieldSelect
            id="prop-col-tier"
            label="Columns"
            value={draft.column_profile ?? ""}
            options={columnOptions}
            disabled={disabled || building}
            onChange={(v) => onFieldChange({ column_profile: v || null })}
          />
          {showTruss && chordOptions.length > 0 ? (
            <FieldSelect
              id="prop-chord-tier"
              label="Truss chords"
              value={draft.truss_chord_profile ?? ""}
              options={chordOptions}
              disabled={disabled || building}
              onChange={(v) => onFieldChange({ truss_chord_profile: v || null })}
            />
          ) : null}
          {showTruss && webOptions.length > 0 ? (
            <FieldSelect
              id="prop-web-tier"
              label="Truss webs"
              value={draft.truss_web_profile ?? ""}
              options={webOptions}
              disabled={disabled || building}
              onChange={(v) => onFieldChange({ truss_web_profile: v || null })}
            />
          ) : null}
          {tieOptions.length > 0 ? (
            <FieldSelect
              id="prop-tie-tier"
              label="Tie beams"
              value={draft.tie_beam_profile ?? ""}
              options={tieOptions}
              disabled={disabled || building}
              onChange={(v) => onFieldChange({ tie_beam_profile: v || null })}
            />
          ) : null}
          <FieldSelect
            id="prop-brace-tier"
            label="Bracing"
            value={draft.bracing_profile ?? ""}
            options={braceOptions}
            disabled={disabled || building}
            onChange={(v) => onFieldChange({ bracing_profile: v || null })}
          />
        </div>
      </details>
    </div>
  );
}

function FieldSelect({
  id,
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <Label htmlFor={id} className="text-[10px] text-muted-foreground">
        {label}
      </Label>
      <select
        id={id}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 flex h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}

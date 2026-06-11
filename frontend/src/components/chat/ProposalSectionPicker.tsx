"use client";

import { ChevronDown, Loader2, Sparkles } from "lucide-react";

import { onboardingTheme } from "@/lib/onboarding-theme";
import { cn } from "@/lib/utils";
import { activeTierFromDraft, tierLabel } from "@/lib/proposal-tier";
import type { GridDefinition } from "@/types/spatial-grid";
import type { SectionTierName, SectionTierPackage, ShedProposalResult } from "@/types/wizard";

type ProposalSectionPickerProps = {
  proposal: ShedProposalResult;
  draft: GridDefinition;
  disabled?: boolean;
  building?: boolean;
  variant?: "default" | "wizard";
  onApplyTier: (tier: SectionTierName) => void;
  onFieldChange: (patch: Partial<GridDefinition>) => void;
  onBuild: () => void;
};

const TIER_ORDER: SectionTierName[] = ["light", "recommended", "conservative"];

const TIER_HINT: Record<SectionTierName, string> = {
  light: "Leaner sections",
  recommended: "Balanced default",
  conservative: "Extra capacity",
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

function TierCard({
  tier,
  package: pkg,
  selected,
  disabled,
  onSelect,
}: {
  tier: SectionTierName;
  package: SectionTierPackage;
  selected: boolean;
  disabled?: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col rounded-2xl border p-4 text-left transition-all duration-200",
        "bg-white/80 backdrop-blur-sm",
        selected
          ? "border-slate-300 shadow-[0_8px_32px_rgba(15,23,42,0.08)] ring-1 ring-slate-200"
          : "border-slate-200/80 hover:border-slate-300 hover:bg-white hover:shadow-sm",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {tierLabel(tier)}
            {tier === "recommended" ? (
              <span className="ml-1 text-amber-500">★</span>
            ) : null}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">{TIER_HINT[tier]}</p>
        </div>
        {selected ? (
          <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">
            Active
          </span>
        ) : null}
      </div>
      <p className="mt-4 font-mono text-lg font-medium tracking-tight text-slate-800">
        {pkg.column_profile}
      </p>
      <p className="mt-1 text-xs text-slate-500">Column section</p>
    </button>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="font-mono text-sm font-medium text-slate-800">{value}</span>
    </div>
  );
}

export function ProposalSectionPicker({
  proposal,
  draft,
  disabled,
  building,
  variant = "default",
  onApplyTier,
  onFieldChange,
  onBuild,
}: ProposalSectionPickerProps) {
  const wizard = variant === "wizard";
  const tiers = proposal.section_tiers ?? [];
  const active =
    activeTierFromDraft(tiers, draft) ?? proposal.active_tier ?? "recommended";
  const activePackage = tiers.find((t) => t.tier === active) ?? tiers[1] ?? tiers[0];

  if (tiers.length === 0 || !activePackage) return null;

  const columnOptions = uniqueOptions(tiers, "column_profile");
  const chordOptions = uniqueOptions(tiers, "truss_chord_profile");
  const webOptions = uniqueOptions(tiers, "truss_web_profile");
  const tieOptions = uniqueOptions(tiers, "tie_beam_profile");
  const braceOptions = uniqueOptions(tiers, "bracing_profile");

  const showTruss = draft.use_truss !== false;

  return (
    <div
      className={cn(
        "space-y-5",
        wizard
          ? "rounded-2xl border bg-white/75 p-5 shadow-[0_8px_40px_rgba(15,23,42,0.06)] backdrop-blur-xl sm:p-6"
          : "rounded-xl border border-border/60 bg-muted/20 p-3",
      )}
      style={wizard ? { borderColor: onboardingTheme.glassBorder } : undefined}
    >
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
          Section package
        </p>
        <p className="mt-1 text-sm text-slate-600">
          Choose a starting steel package — refine individual members anytime.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {TIER_ORDER.map((tier) => {
          const pkg = tiers.find((t) => t.tier === tier);
          if (!pkg) return null;
          return (
            <TierCard
              key={tier}
              tier={tier}
              package={pkg}
              selected={active === tier}
              disabled={disabled || building}
              onSelect={() => onApplyTier(tier)}
            />
          );
        })}
      </div>

      <div
        className={cn(
          "rounded-xl border px-4 py-1",
          wizard ? "border-slate-200/80 bg-slate-50/50" : "border-border/50 bg-background/60",
        )}
      >
        <ProfileRow label="Columns" value={activePackage.column_profile} />
        {showTruss ? (
          <>
            <ProfileRow
              label="Truss chords"
              value={activePackage.truss_chord_profile ?? "—"}
            />
            <ProfileRow
              label="Truss webs"
              value={activePackage.truss_web_profile ?? "—"}
            />
          </>
        ) : null}
        <ProfileRow label="Tie beams" value={activePackage.tie_beam_profile ?? "IPE200"} />
        <ProfileRow label="Bracing" value={activePackage.bracing_profile} />
      </div>

      <button
        type="button"
        disabled={disabled || building}
        onClick={onBuild}
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-xl text-sm font-medium text-white transition-all duration-200",
          "bg-slate-900 shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400",
          wizard ? "h-12" : "h-10",
        )}
      >
        {building ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Building model…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Build model
          </>
        )}
      </button>

      <details className="group rounded-xl border border-slate-200/80 bg-white/50">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-medium text-slate-600 marker:content-none hover:text-slate-900">
          Advanced — edit sections
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-180" />
        </summary>
        <div className="grid gap-3 border-t border-slate-100 px-4 py-4 sm:grid-cols-2">
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
      <label htmlFor={id} className="text-xs font-medium text-slate-500">
        {label}
      </label>
      <select
        id={id}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 focus:border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-100"
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

"use client";

import { Loader2, Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type { GridDefinition } from "@/types/spatial-grid";
import type { ShedProposalResult } from "@/types/wizard";

type EngineeringProposalPanelProps = {
  proposal: ShedProposalResult;
  draft: GridDefinition;
  disabled?: boolean;
  building?: boolean;
  onChange: (patch: Partial<GridDefinition>) => void;
  onBack?: () => void;
  onBuild: () => void;
  compact?: boolean;
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
      <Label htmlFor={id} className="text-xs font-medium text-slate-700">
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

export function EngineeringProposalPanel({
  proposal,
  draft,
  disabled,
  building,
  onChange,
  onBack,
  onBuild,
  compact,
}: EngineeringProposalPanelProps) {
  const nFrames = draft.z_spans.length + 1;
  const trussLabel = draft.use_truss
    ? (draft.truss_type ?? "pratt").replace(/_/g, " ")
    : "Portal rafters";

  if (compact) {
    return (
      <div className="space-y-3 rounded-xl border border-border/60 bg-muted/20 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Adjust before build
        </p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <Label className="text-muted-foreground">Column</Label>
            <Input
              value={draft.column_profile ?? ""}
              disabled={disabled}
              onChange={(e) => onChange({ column_profile: e.target.value || null })}
              className="mt-0.5 h-8 text-xs"
            />
          </div>
          <div>
            <Label className="text-muted-foreground">Bracing</Label>
            <Input
              value={draft.bracing_profile ?? ""}
              disabled={disabled}
              onChange={(e) => onChange({ bracing_profile: e.target.value || null })}
              className="mt-0.5 h-8 text-xs"
            />
          </div>
        </div>
        <p className="font-mono text-[10px] text-muted-foreground">
          {nFrames} frames · {trussLabel} · bays{" "}
          {draft.z_spans.map((s) => `${(s / 1000).toFixed(1)}m`).join(" + ")}
        </p>
        <div className="divide-y divide-border/60 border-t border-border/60 pt-1">
          <ToggleRow
            id="prop-truss"
            label="Roof truss"
            checked={Boolean(draft.use_truss)}
            disabled={disabled}
            onCheckedChange={(v) =>
              onChange({ use_truss: v, truss_type: v ? "pratt" : "none" })
            }
          />
          <ToggleRow
            id="prop-x"
            label="Wall X-bracing"
            checked={Boolean(draft.x_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ x_bracing: v })}
          />
          <ToggleRow
            id="prop-roof-x"
            label="Roof X-bracing"
            checked={Boolean(draft.roof_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ roof_bracing: v })}
          />
          <ToggleRow
            id="prop-gable-x"
            label="Gable X-bracing"
            checked={Boolean(draft.gable_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ gable_bracing: v })}
          />
          <ToggleRow
            id="prop-sag"
            label="Anti-sag rods"
            checked={Boolean(draft.sag_rods)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ sag_rods: v })}
          />
          <ToggleRow
            id="prop-girts"
            label="Wall girts"
            checked={draft.generate_wall_girts !== false}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ generate_wall_girts: v })}
          />
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
              Building structure…
            </>
          ) : (
            <>
              <Rocket className="h-4 w-4" />
              Build structure
            </>
          )}
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-xl border border-white/40 bg-white/35 p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
          Preliminary structural proposal
        </p>
        <p className="mt-1 text-sm font-medium text-slate-800">{proposal.summary}</p>
        <ul className="mt-3 space-y-1.5 text-xs leading-relaxed text-slate-600">
          {proposal.rationale.map((line) => (
            <li key={line.slice(0, 48)} className="flex gap-2">
              <span className="text-primary">•</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-white/40 bg-white/30 p-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Adjust before build
        </p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <Label className="text-slate-600">Column</Label>
            <Input
              value={draft.column_profile ?? ""}
              disabled={disabled}
              onChange={(e) => onChange({ column_profile: e.target.value || null })}
              className="mt-0.5 h-8 bg-white/80 text-xs"
            />
          </div>
          <div>
            <Label className="text-slate-600">Truss chord</Label>
            <Input
              value={draft.truss_chord_profile ?? ""}
              disabled={disabled || !draft.use_truss}
              onChange={(e) =>
                onChange({ truss_chord_profile: e.target.value || null })
              }
              className="mt-0.5 h-8 bg-white/80 text-xs"
            />
          </div>
          <div>
            <Label className="text-slate-600">Truss web</Label>
            <Input
              value={draft.truss_web_profile ?? ""}
              disabled={disabled || !draft.use_truss}
              onChange={(e) => onChange({ truss_web_profile: e.target.value || null })}
              className="mt-0.5 h-8 bg-white/80 text-xs"
            />
          </div>
          <div>
            <Label className="text-slate-600">Bracing</Label>
            <Input
              value={draft.bracing_profile ?? ""}
              disabled={disabled}
              onChange={(e) => onChange({ bracing_profile: e.target.value || null })}
              className="mt-0.5 h-8 bg-white/80 text-xs"
            />
          </div>
        </div>
        <p className="mt-2 font-mono text-[10px] text-slate-500">
          {nFrames} frames · {trussLabel} · bays{" "}
          {draft.z_spans.map((s) => `${(s / 1000).toFixed(1)}m`).join(" + ")}
        </p>
        <div className="mt-3 divide-y divide-slate-200/60 border-t border-slate-200/60 pt-2">
          <ToggleRow
            id="prop-truss"
            label="Roof truss"
            checked={Boolean(draft.use_truss)}
            disabled={disabled}
            onCheckedChange={(v) =>
              onChange({ use_truss: v, truss_type: v ? "pratt" : "none" })
            }
          />
          <ToggleRow
            id="prop-x"
            label="Wall X-bracing"
            checked={Boolean(draft.x_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ x_bracing: v })}
          />
          <ToggleRow
            id="prop-roof-x"
            label="Roof X-bracing"
            checked={Boolean(draft.roof_bracing)}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ roof_bracing: v })}
          />
          <ToggleRow
            id="prop-purlins"
            label="Roof purlins"
            checked={draft.generate_purlins !== false}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ generate_purlins: v })}
          />
          <ToggleRow
            id="prop-girts"
            label="Wall girts"
            checked={draft.generate_wall_girts !== false}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ generate_wall_girts: v })}
          />
          <ToggleRow
            id="prop-ties"
            label="Longitudinal ties"
            checked={draft.generate_tie_beams !== false}
            disabled={disabled}
            onCheckedChange={(v) => onChange({ generate_tie_beams: v })}
          />
        </div>
      </div>

      <div className="flex gap-2">
        {onBack ? (
          <Button type="button" variant="outline" disabled={disabled || building} onClick={onBack}>
            Back
          </Button>
        ) : null}
        <Button
          type="button"
          disabled={disabled || building}
          onClick={onBuild}
          className="flex-1 gap-2 bg-slate-900 hover:bg-slate-800"
        >
          {building ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Building structure…
            </>
          ) : (
            <>
              <Rocket className="h-4 w-4" />
              Build structure
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

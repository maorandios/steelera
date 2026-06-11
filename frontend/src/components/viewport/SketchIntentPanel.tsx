"use client";

import { ChevronRight, Loader2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { intentLabel, recommendProfiles } from "@/lib/structural-intent";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import { SKETCH_INTENT_OPTIONS } from "@/types/sketch";

const SCOPE_OPTIONS = [
  { id: "all_bays" as const, label: "All bays" },
  { id: "row" as const, label: "This row" },
  { id: "single" as const, label: "Just here" },
];

function OptionRow({
  label,
  detail,
  active,
  recommended,
  onClick,
}: {
  label: string;
  detail?: string;
  active?: boolean;
  recommended?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between gap-2 border-b border-border/60 px-3 py-2.5 text-left text-sm transition-colors",
        "hover:bg-muted/40",
        active && "bg-muted/50",
      )}
    >
      <span className="min-w-0">
        <span className="font-medium">{label}</span>
        {recommended ? (
          <span className="ml-1.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-600">
            suggested
          </span>
        ) : null}
        {detail ? (
          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
            {detail}
          </span>
        ) : null}
      </span>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-40" />
    </button>
  );
}

export function SketchIntentPanel() {
  const sketchSession = useProjectStore((s) => s.sketchSession);
  const busy = useProjectStore((s) => s.isLoading || s.isMacroLoading);
  const selectSketchOperation = useProjectStore((s) => s.selectSketchOperation);
  const setSketchIntentOverride = useProjectStore((s) => s.setSketchIntentOverride);
  const selectSketchProfile = useProjectStore((s) => s.selectSketchProfile);
  const setSketchApplyScope = useProjectStore((s) => s.setSketchApplyScope);
  const commitSketchElement = useProjectStore((s) => s.commitSketchElement);
  const cancelSketchMode = useProjectStore((s) => s.cancelSketchMode);
  const [showTypePicker, setShowTypePicker] = useState(false);

  const analysis = sketchSession.analysis;
  const operations = analysis?.operations ?? [];
  const selectedOp = operations.find(
    (o) => o.id === sketchSession.selectedOperationId,
  );
  const kind =
    sketchSession.intentOverride ??
    (sketchSession.intent?.kind as import("@/types/sketch").StructuralIntentKind | undefined) ??
    "unknown";
  const label = selectedOp?.label ?? intentLabel(kind as "unknown");
  const spanMm = sketchSession.intent?.spanMm ?? 0;

  const profiles = useMemo(() => {
    if (selectedOp?.profile_suggestions?.length) {
      return selectedOp.profile_suggestions;
    }
    if (analysis?.profiles?.length) return analysis.profiles;
    return recommendProfiles(spanMm, kind as "unknown").map((profile, i) => ({
      profile,
      tier: i === 0 ? ("recommended" as const) : ("light" as const),
      tier_label: i === 0 ? "Optimal" : "Light",
      utilization: 0,
      governing: "span_rule",
    }));
  }, [selectedOp?.profile_suggestions, analysis?.profiles, spanMm, kind]);

  if (sketchSession.phase !== "dialogue") return null;

  const detected =
    sketchSession.intent?.label ??
    intentLabel(kind as "unknown");
  const suggestedScope =
    selectedOp?.scope_suggestion ?? analysis?.scope_suggestion ?? "single";

  const stepTitle =
    sketchSession.dialogueStep === 1
      ? "What to place?"
      : sketchSession.dialogueStep === 2
        ? "Profile"
        : "Where?";

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-card shadow-sm",
        (busy || sketchSession.analysisLoading) && "pointer-events-none opacity-60",
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-2">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Sketch · step {sketchSession.dialogueStep}/3
          </p>
          <p className="truncate text-sm font-medium text-foreground">
            {sketchSession.analysisLoading ? "Analyzing…" : stepTitle}
          </p>
        </div>
        <button
          type="button"
          className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={cancelSketchMode}
          aria-label="Cancel sketch"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {sketchSession.analysisLoading ? (
        <div className="flex items-center gap-2 px-3 py-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Reading your line…
        </div>
      ) : null}

      {sketchSession.dialogueStep === 1 && !sketchSession.analysisLoading ? (
        <>
          <p className="border-b border-border/60 px-3 py-2 text-xs text-muted-foreground">
            Detected: <span className="font-medium text-foreground">{detected}</span>
          </p>
          {operations.length === 0 ? (
            <p className="px-3 py-3 text-xs text-amber-700">
              No options — is the backend running?
            </p>
          ) : (
            <div>
              {operations.map((op) => (
                <OptionRow
                  key={op.id}
                  label={op.label}
                  active={op.id === sketchSession.selectedOperationId}
                  recommended={op.recommended}
                  onClick={() => selectSketchOperation(op.id)}
                />
              ))}
            </div>
          )}
          {sketchSession.selectedOperationId && operations.length > 0 ? (
            <div className="border-t border-border/60 p-2">
              <button
                type="button"
                className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
                onClick={() => selectSketchOperation(sketchSession.selectedOperationId!)}
              >
                Continue
              </button>
            </div>
          ) : null}
          <div className="border-t border-border/60 px-3 py-2">
            <button
              type="button"
              className="text-xs text-muted-foreground underline hover:text-foreground"
              onClick={() => setShowTypePicker((v) => !v)}
            >
              Wrong type?
            </button>
            {showTypePicker ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {SKETCH_INTENT_OPTIONS.map((opt) => (
                  <button
                    key={opt.kind}
                    type="button"
                    className="rounded-full border border-border px-2.5 py-1 text-xs hover:bg-muted"
                    onClick={() => {
                      void setSketchIntentOverride(opt.kind);
                      setShowTypePicker(false);
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </>
      ) : null}

      {sketchSession.dialogueStep === 2 && !sketchSession.analysisLoading ? (
        <>
          <p className="border-b border-border/60 px-3 py-2 text-xs text-muted-foreground">
            {label} · {Math.round(spanMm).toLocaleString()} mm
          </p>
          <div>
            {profiles.map((option) => (
              <OptionRow
                key={option.profile}
                label={option.profile}
                detail={option.tier_label ?? undefined}
                recommended={option.tier === "recommended"}
                onClick={() => selectSketchProfile(option.profile)}
              />
            ))}
          </div>
          <div className="border-t border-border/60 p-2">
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={() =>
                useProjectStore.setState({
                  sketchSession: { ...sketchSession, dialogueStep: 1 },
                })
              }
            >
              ← Back
            </button>
          </div>
        </>
      ) : null}

      {sketchSession.dialogueStep === 3 && !sketchSession.analysisLoading ? (
        <>
          <p className="border-b border-border/60 px-3 py-2 text-xs text-muted-foreground">
            {sketchSession.selectedProfile} · {label}
          </p>
          <div>
            {SCOPE_OPTIONS.map((opt) => (
              <OptionRow
                key={opt.id}
                label={opt.label}
                recommended={opt.id === suggestedScope}
                onClick={() => {
                  void commitSketchElement(opt.id);
                }}
              />
            ))}
          </div>
          <div className="border-t border-border/60 p-2">
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={() =>
                useProjectStore.setState({
                  sketchSession: { ...sketchSession, dialogueStep: 2 },
                })
              }
            >
              ← Back
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { intentLabel, recommendProfiles } from "@/lib/structural-intent";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import { SKETCH_INTENT_OPTIONS } from "@/types/sketch";

const SCOPE_LABELS = {
  all_bays: "Apply to All Bays",
  row: "This Row Only",
  single: "Just Here",
} as const;

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

  const summary =
    analysis?.summary ??
    analysis?.message ??
    `I detected a ${intentLabel(kind as "unknown").toLowerCase()}.`;

  const suggestedScope =
    selectedOp?.scope_suggestion ?? analysis?.scope_suggestion ?? "single";
  const scopeReason = analysis?.scope_reason;

  return (
    <div
      className={cn(
        "rounded-t-2xl border border-slate-200 bg-white px-4 py-4 shadow-2xl",
        (busy || sketchSession.analysisLoading) && "pointer-events-none opacity-60",
      )}
    >
      {sketchSession.analysisLoading ? (
        <p className="text-base text-slate-600">Analyzing sketch…</p>
      ) : null}

      {sketchSession.dialogueStep === 1 && !sketchSession.analysisLoading ? (
        <>
          <p className="text-base leading-relaxed text-slate-800">{summary}</p>
          {analysis?.ai_available ? (
            <p className="mt-1 text-xs text-slate-500">AI-assisted advice</p>
          ) : analysis ? (
            <p className="mt-1 text-xs text-slate-500">Engineering recommendations</p>
          ) : null}
          <p className="mt-3 text-sm font-medium text-slate-700">
            What should we do?
          </p>
          {operations.length === 0 ? (
            <p className="mt-2 text-sm text-amber-700">
              No operations available — check that the backend is running on port 8000.
            </p>
          ) : (
            <div className="mt-2 flex flex-col gap-2">
              {operations.map((op) => (
                <Button
                  key={op.id}
                  type="button"
                  variant={
                    op.id === sketchSession.selectedOperationId || op.recommended
                      ? "default"
                      : "outline"
                  }
                  className="h-auto min-h-11 flex-col items-start gap-0.5 py-2 text-left text-sm"
                  onClick={() => selectSketchOperation(op.id)}
                >
                  <span className="font-medium">
                    {op.label}
                    {op.recommended ? " (Recommended)" : ""}
                  </span>
                  <span className="text-xs opacity-80">{op.description}</span>
                  {op.warnings.length > 0 ? (
                    <span className="text-xs text-amber-700">{op.warnings[0]}</span>
                  ) : null}
                </Button>
              ))}
            </div>
          )}
          {sketchSession.selectedOperationId && operations.length > 0 ? (
            <Button
              type="button"
              className="mt-3 h-11 w-full text-sm"
              onClick={() => selectSketchOperation(sketchSession.selectedOperationId!)}
            >
              Continue with selected option
            </Button>
          ) : null}
          <button
            type="button"
            className="mt-3 text-sm text-slate-500 underline hover:text-slate-700"
            onClick={() => setShowTypePicker((v) => !v)}
          >
            Wrong element type?
          </button>
          {showTypePicker ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {SKETCH_INTENT_OPTIONS.map((opt) => (
                <button
                  key={opt.kind}
                  type="button"
                  className="rounded-full border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50"
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
        </>
      ) : null}

      {sketchSession.dialogueStep === 2 && !sketchSession.analysisLoading ? (
        <>
          <p className="text-base leading-relaxed text-slate-800">
            <span className="font-semibold">{label}</span>
            {" — "}
            pick profile for {Math.round(spanMm).toLocaleString()} mm span:
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {profiles.map((option) => (
              <Button
                key={option.profile}
                type="button"
                variant={option.tier === "recommended" ? "default" : "outline"}
                className="h-11 justify-start text-sm"
                onClick={() => selectSketchProfile(option.profile)}
              >
                <span className="flex flex-col items-start gap-0.5">
                  <span>
                    {option.profile}
                    {option.tier_label ? ` (${option.tier_label})` : ""}
                  </span>
                  {option.utilization > 0 ? (
                    <span className="text-xs opacity-80">
                      {Math.round(option.utilization * 100)}% util · {option.governing}
                    </span>
                  ) : null}
                </span>
              </Button>
            ))}
          </div>
          <button
            type="button"
            className="mt-3 text-sm text-slate-500 hover:text-slate-700"
            onClick={() =>
              useProjectStore.setState({
                sketchSession: {
                  ...sketchSession,
                  dialogueStep: 1,
                },
              })
            }
          >
            ← Change operation
          </button>
        </>
      ) : null}

      {sketchSession.dialogueStep === 3 && !sketchSession.analysisLoading ? (
        <>
          <p className="text-base leading-relaxed text-slate-800">
            Apply <span className="font-semibold">{sketchSession.selectedProfile}</span>{" "}
            {label} across matching layout?
          </p>
          {scopeReason ? (
            <p className="mt-1 text-sm text-slate-500">{scopeReason}</p>
          ) : null}
          <div className="mt-3 flex flex-col gap-2">
            <Button
              type="button"
              className={cn(
                "h-11 text-sm",
                suggestedScope === "all_bays" && "ring-2 ring-slate-300",
              )}
              onClick={() => {
                setSketchApplyScope("all_bays");
                void commitSketchElement();
              }}
            >
              {SCOPE_LABELS.all_bays}
            </Button>
            <Button
              type="button"
              variant="outline"
              className={cn(
                "h-11 text-sm",
                suggestedScope === "row" && "ring-2 ring-slate-300",
              )}
              onClick={() => {
                setSketchApplyScope("row");
                void commitSketchElement();
              }}
            >
              {SCOPE_LABELS.row}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className={cn(
                "h-11 text-sm",
                suggestedScope === "single" && "ring-2 ring-slate-300",
              )}
              onClick={() => {
                setSketchApplyScope("single");
                void commitSketchElement();
              }}
            >
              {SCOPE_LABELS.single}
            </Button>
          </div>
        </>
      ) : null}

      <button
        type="button"
        className="mt-4 w-full py-1 text-center text-sm text-slate-500 hover:text-slate-700"
        onClick={cancelSketchMode}
      >
        Cancel sketch
      </button>
    </div>
  );
}

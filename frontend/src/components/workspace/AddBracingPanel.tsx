"use client";

import { ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BRACING_PROFILE_OPTIONS } from "@/lib/element-registry";
import { oppositeGableEnd, oppositeSideWallLabel } from "@/lib/wall-panel";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { AddBracingScope } from "@/types/add-element";

function OptionRow({
  label,
  detail,
  active,
  onClick,
}: {
  label: string;
  detail?: string;
  active?: boolean;
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
        {detail ? (
          <span className="mt-0.5 block text-xs text-muted-foreground">{detail}</span>
        ) : null}
      </span>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-40" />
    </button>
  );
}

export function AddBracingPanel() {
  const session = useProjectStore((s) => s.addElementSession);
  const structuralGrid = useProjectStore((s) => s.structuralGrid);
  const busy = useProjectStore((s) => s.isLoading || s.isMacroLoading);
  const cancelAddElement = useProjectStore((s) => s.cancelAddElement);
  const setAddBracingProfile = useProjectStore((s) => s.setAddBracingProfile);
  const commitAddBracing = useProjectStore((s) => s.commitAddBracing);
  const [profileInput, setProfileInput] = useState("");

  const profiles = useMemo(() => [...BRACING_PROFILE_OPTIONS], []);

  useEffect(() => {
    if (session?.type === "bracing" && session.step === "profile") {
      setProfileInput(session.profile);
    }
  }, [session?.step, session?.type, session?.profile]);

  const scopeOptions = useMemo((): {
    id: AddBracingScope;
    label: string;
    detail: string;
  }[] => {
    const panel = session?.type === "bracing" ? session.panel : null;
    if (!panel) return [];

    if (panel.kind === "gable_wall") {
      const otherEnd = oppositeGableEnd(panel.end);
      const otherLabel = otherEnd === "near" ? "Near gable" : "Far gable";
      return [
        {
          id: "this_panel",
          label: "This panel only",
          detail: `Frame ${panel.frameZ} · ${panel.xStart} → ${panel.xEnd}`,
        },
        {
          id: "parallel_bay",
          label: "Opposite gable end too",
          detail: `${otherLabel} · ${panel.xStart} → ${panel.xEnd}`,
        },
        {
          id: "all_bays_wall",
          label: "All bays on this gable end",
          detail: `Every X bay along frame ${panel.frameZ}`,
        },
        {
          id: "both_walls",
          label: "Both gable ends",
          detail: "Near and far end walls, all X bays",
        },
      ];
    }

    const parallelWall = oppositeSideWallLabel(panel.wallXLabel, structuralGrid);
    const parallelDetail =
      parallelWall
        ? `Wall ${panel.wallXLabel} and ${parallelWall} · Bay ${panel.zStart} → ${panel.zEnd}`
        : "Same bay on the opposite side wall";

    return [
      {
        id: "this_panel",
        label: "This panel only",
        detail: "One bay on the selected wall",
      },
      {
        id: "parallel_bay",
        label: "The parallel bay too",
        detail: parallelDetail,
      },
      {
        id: "portal_bay",
        label: "Full portal bay",
        detail: `Both side walls + roof · Bay ${panel.zStart} → ${panel.zEnd}`,
      },
      {
        id: "all_bays_wall",
        label: "All bays on this wall",
        detail: "Full X in every bay along the wall",
      },
      {
        id: "both_walls",
        label: "Both side walls",
        detail: "Every bay on walls A and B",
      },
    ];
  }, [session, structuralGrid]);

  if (!session || session.type !== "bracing") {
    return null;
  }

  const stepTitle =
    session.step === "pick_panel"
      ? "Pick wall panel"
      : session.step === "profile"
        ? "Section profile"
        : "Apply scope";

  const stepNum =
    session.step === "pick_panel" ? 1 : session.step === "profile" ? 2 : 3;

  const applyProfileInput = () => {
    const value = profileInput.trim().toUpperCase();
    if (!value) return;
    setAddBracingProfile(value);
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-card shadow-sm",
        busy && "pointer-events-none opacity-60",
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-2">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Add bracing · step {stepNum}/3
          </p>
          <p className="truncate text-sm font-medium">{stepTitle}</p>
          {session.panel ? (
            <p className="truncate text-xs text-muted-foreground">
              {session.panel.label} · Full X
            </p>
          ) : null}
        </div>
        <button
          type="button"
          className="rounded-md p-1 text-muted-foreground hover:bg-muted"
          onClick={cancelAddElement}
          aria-label="Cancel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {session.step === "pick_panel" ? (
        <p className="px-3 py-3 text-xs leading-relaxed text-muted-foreground">
          Hover a panel between columns — side walls and gable ends highlight
          blue. Click to select one bay.
        </p>
      ) : null}

      {session.step === "profile" ? (
        <div>
          <div className="space-y-2 border-b border-border/60 px-3 py-3">
            <p className="text-xs text-muted-foreground">
              Type any catalog section (e.g. L80x80x8, SHS100x100x5)
            </p>
            <div className="flex gap-2">
              <Input
                value={profileInput}
                onChange={(e) => setProfileInput(e.target.value)}
                placeholder="Profile designation…"
                className="h-9 flex-1 text-sm"
                autoComplete="off"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    applyProfileInput();
                  }
                }}
              />
              <Button
                type="button"
                size="sm"
                className="h-9 shrink-0"
                disabled={!profileInput.trim()}
                onClick={applyProfileInput}
              >
                Continue
              </Button>
            </div>
          </div>
          <p className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Common sections
          </p>
          {profiles.map((profile) => (
            <OptionRow
              key={profile}
              label={profile}
              active={session.profile === profile}
              onClick={() => setAddBracingProfile(profile)}
            />
          ))}
        </div>
      ) : null}

      {session.step === "scope" ? (
        <div>
          {scopeOptions.map((opt) => (
            <OptionRow
              key={opt.id}
              label={opt.label}
              detail={opt.detail}
              onClick={() => void commitAddBracing(opt.id)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

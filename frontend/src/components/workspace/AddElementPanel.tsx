"use client";

import { ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  BRACING_PROFILE_OPTIONS,
  COLUMN_PROFILE_OPTIONS,
  RAFTER_PROFILE_OPTIONS,
} from "@/lib/element-registry";
import {
  COLUMN_TRUSS_POSITION_OPTIONS,
  COLUMN_WALL_POSITION_OPTIONS,
} from "@/lib/column-panel-placement";
import {
  oppositeGableEnd,
  oppositeRoofSlope,
  oppositeSideWallLabel,
} from "@/lib/wall-panel";
import {
  TIE_BEAM_LOCATION_OPTIONS,
  TIE_BEAM_TRUSS_LOCATION_OPTIONS,
} from "@/lib/tie-panel-placement";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { AddBracingScope, AddColumnScope, AddTieBeamScope } from "@/types/add-element";

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

export function AddElementPanel() {
  const session = useProjectStore((s) => s.addElementSession);
  const structuralGrid = useProjectStore((s) => s.structuralGrid);
  const busy = useProjectStore((s) => s.isLoading || s.isMacroLoading);
  const cancelAddElement = useProjectStore((s) => s.cancelAddElement);
  const selectAddElementKind = useProjectStore((s) => s.selectAddElementKind);
  const setAddBracingProfile = useProjectStore((s) => s.setAddBracingProfile);
  const setAddTieBeamChord = useProjectStore((s) => s.setAddTieBeamChord);
  const setAddTieBeamProfile = useProjectStore((s) => s.setAddTieBeamProfile);
  const setAddColumnProfile = useProjectStore((s) => s.setAddColumnProfile);
  const selectAddColumnPosition = useProjectStore((s) => s.selectAddColumnPosition);
  const setAddColumnConnect = useProjectStore((s) => s.setAddColumnConnect);
  const commitAddColumnScope = useProjectStore((s) => s.commitAddColumnScope);
  const setAddBracingBraceCount = useProjectStore((s) => s.setAddBracingBraceCount);
  const commitAddBracing = useProjectStore((s) => s.commitAddBracing);
  const selectAddTieBeamLocation = useProjectStore((s) => s.selectAddTieBeamLocation);
  const commitAddTieBeamScope = useProjectStore((s) => s.commitAddTieBeamScope);
  const [profileInput, setProfileInput] = useState("");
  const [braceCountDraft, setBraceCountDraft] = useState(1);

  const quickBracingProfiles = useMemo(() => BRACING_PROFILE_OPTIONS.slice(0, 3), []);
  const quickTieProfiles = useMemo(() => RAFTER_PROFILE_OPTIONS.slice(0, 3), []);
  const quickColumnProfiles = useMemo(() => COLUMN_PROFILE_OPTIONS.slice(0, 3), []);

  useEffect(() => {
    if (
      session &&
      "type" in session &&
      session.step === "profile"
    ) {
      setProfileInput(session.profile);
    }
  }, [session]);

  useEffect(() => {
    if (
      session &&
      "type" in session &&
      session.type === "bracing" &&
      session.step === "brace_count"
    ) {
      setBraceCountDraft(session.braceCount);
    }
  }, [session]);

  const scopeOptions = useMemo((): {
    id: AddBracingScope;
    label: string;
    detail: string;
  }[] => {
    const panel =
      session && "type" in session && session.type === "bracing"
        ? session.panel
        : null;
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
      ];
    }

    if (panel.kind === "roof") {
      const otherSlope = oppositeRoofSlope(panel.slopeSide);
      const slopeLabel =
        panel.slopeSide === "left"
          ? "Left slope"
          : panel.slopeSide === "right"
            ? "Right slope"
            : "Roof slope";
      const options: {
        id: AddBracingScope;
        label: string;
        detail: string;
      }[] = [
        {
          id: "this_panel",
          label: "This panel only",
          detail: `${slopeLabel} · Frame ${panel.zStart} → ${panel.zEnd}`,
        },
      ];
      if (otherSlope) {
        const otherLabel = otherSlope === "left" ? "Left slope" : "Right slope";
        options.push({
          id: "parallel_bay",
          label: "Other roof slope too",
          detail: `${otherLabel} · Frame ${panel.zStart} → ${panel.zEnd}`,
        });
      }
      options.push({
        id: "portal_bay",
        label: "Full portal frame",
        detail: `Both side walls (every column bay) + all roof slopes · Frame ${panel.zStart} → ${panel.zEnd}`,
      });
      options.push({
        id: "all_bays_wall",
        label: "All frame bays on this slope",
        detail: `Full X on ${slopeLabel.toLowerCase()} at every frame bay`,
      });
      return options;
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

  const tieScopeOptions = useMemo((): {
    id: AddTieBeamScope;
    label: string;
    detail: string;
  }[] => {
    const panel =
      session && "type" in session && session.type === "tie_beam"
        ? session.panel
        : null;
    if (!panel || panel.kind !== "roof") return [];

    const slopeLabel =
      panel.slopeSide === "left"
        ? "Left slope"
        : panel.slopeSide === "right"
          ? "Right slope"
          : "Roof slope";
    const otherSlope = oppositeRoofSlope(panel.slopeSide);
    const locationLabel =
      session &&
      "type" in session &&
      session.type === "tie_beam" &&
      session.location
        ? TIE_BEAM_TRUSS_LOCATION_OPTIONS.find((o) => o.id === session.location)
            ?.label ?? session.location
        : "selected location";

    const options: {
      id: AddTieBeamScope;
      label: string;
      detail: string;
    }[] = [
      {
        id: "this_panel",
        label: "This panel only",
        detail: `${slopeLabel} · Frame ${panel.zStart} → ${panel.zEnd} · ${locationLabel}`,
      },
      {
        id: "all_bays_slope",
        label: "Full row on this slope",
        detail: `Every frame bay on ${slopeLabel.toLowerCase()} at ${locationLabel}`,
      },
    ];

    if (otherSlope) {
      const otherLabel = otherSlope === "left" ? "Left slope" : "Right slope";
      options.push({
        id: "parallel_slope",
        label: "Both roof slopes",
        detail: `${slopeLabel} and ${otherLabel} · Frame ${panel.zStart} → ${panel.zEnd} · ${locationLabel}`,
      });
      options.push({
        id: "all_trusses",
        label: "All trusses both slopes",
        detail: `Every frame bay on both slopes at ${locationLabel}`,
      });
    }

    return options;
  }, [session]);

  const columnScopeOptions = useMemo((): {
    id: AddColumnScope;
    label: string;
    detail: string;
  }[] => {
    const panel =
      session && "type" in session && session.type === "column"
        ? session.panel
        : null;
    if (!panel) return [];

    const positionLabel =
      session &&
      "type" in session &&
      session.type === "column" &&
      session.position
        ? (panel.kind === "roof"
            ? COLUMN_TRUSS_POSITION_OPTIONS
            : COLUMN_WALL_POSITION_OPTIONS
          ).find((o) => o.id === session.position)?.label ?? session.position
        : "selected position";

    if (panel.kind === "gable_wall") {
      return [
        {
          id: "this_panel",
          label: "This panel only",
          detail: `Frame ${panel.frameZ} · ${panel.xStart} → ${panel.xEnd} · ${positionLabel}`,
        },
        {
          id: "all_bays_wall",
          label: "All bays on this gable end",
          detail: `Every X bay along frame ${panel.frameZ} at ${positionLabel}`,
        },
      ];
    }

    if (panel.kind === "roof") {
      const slopeLabel =
        panel.slopeSide === "left"
          ? "Left slope"
          : panel.slopeSide === "right"
            ? "Right slope"
            : "Roof slope";
      const otherSlope = oppositeRoofSlope(panel.slopeSide);
      const options: {
        id: AddColumnScope;
        label: string;
        detail: string;
      }[] = [
        {
          id: "this_panel",
          label: "This panel only",
          detail: `${slopeLabel} · Frame ${panel.zStart} → ${panel.zEnd} · ${positionLabel}`,
        },
        {
          id: "all_bays_slope",
          label: "Full row on this slope",
          detail: `Every frame bay on ${slopeLabel.toLowerCase()} at ${positionLabel}`,
        },
      ];
      if (otherSlope) {
        const otherLabel = otherSlope === "left" ? "Left slope" : "Right slope";
        options.push({
          id: "parallel_slope",
          label: "Both roof slopes",
          detail: `${slopeLabel} and ${otherLabel} · Frame ${panel.zStart} → ${panel.zEnd} · ${positionLabel}`,
        });
        options.push({
          id: "all_trusses",
          label: "All trusses both slopes",
          detail: `Every frame bay on both slopes at ${positionLabel}`,
        });
      }
      return options;
    }

    const parallelWall = oppositeSideWallLabel(panel.wallXLabel, structuralGrid);
    return [
      {
        id: "this_panel",
        label: "This panel only",
        detail: `Wall ${panel.wallXLabel} · Bay ${panel.zStart} → ${panel.zEnd} · ${positionLabel}`,
      },
      {
        id: "all_bays_wall",
        label: "All bays on this wall",
        detail: `Every bay along wall ${panel.wallXLabel} at ${positionLabel}`,
      },
      {
        id: "both_walls",
        label: "Both side walls",
        detail: parallelWall
          ? `Walls ${panel.wallXLabel} and ${parallelWall} at ${positionLabel}`
          : `Both side walls at ${positionLabel}`,
      },
    ];
  }, [session, structuralGrid]);

  if (!session) {
    return null;
  }

  if (session.step === "choose_kind") {
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
              Add element
            </p>
            <p className="truncate text-sm font-medium">What do you want to add?</p>
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
        <OptionRow
          label="Bracing"
          detail="X-braces on wall, gable, or roof panels"
          onClick={() => selectAddElementKind("bracing")}
        />
        <OptionRow
          label="Tie beam"
          detail="Longitudinal tie on wall, gable, or truss panels"
          onClick={() => selectAddElementKind("tie_beam")}
        />
        <OptionRow
          label="Column"
          detail="Vertical column in a wall bay or under trusses / rafters"
          onClick={() => selectAddElementKind("column")}
        />
      </div>
    );
  }

  if (!("type" in session)) {
    return null;
  }

  const isBracing = session.type === "bracing";
  const isTie = session.type === "tie_beam";
  const isColumn = session.type === "column";
  const isRoofTiePanel = isTie && session.panel?.kind === "roof";
  const isRoofColumnPanel = isColumn && session.panel?.kind === "roof";

  const stepTitle = isBracing
    ? session.step === "pick_panel"
      ? "Pick bracing panel"
      : session.step === "profile"
        ? "Section profile"
        : session.step === "brace_count"
          ? "X-braces per panel"
          : "Apply scope"
    : isColumn
      ? session.step === "pick_panel"
        ? "Pick column bay"
        : session.step === "profile"
          ? "Section profile"
          : session.step === "position"
            ? "Pick position"
            : session.step === "connect"
              ? "Top connection"
              : "Apply scope"
      : session.step === "pick_panel"
        ? "Pick tie beam panel"
        : session.step === "chord"
          ? "Chord"
          : session.step === "profile"
            ? "Section profile"
            : session.step === "location"
              ? "Pick location"
              : "Apply scope";

  const stepNum = isBracing
    ? session.step === "pick_panel"
      ? 2
      : session.step === "profile"
        ? 3
        : session.step === "brace_count"
          ? 4
          : 5
    : isColumn
      ? session.step === "pick_panel"
        ? 2
        : session.step === "profile"
          ? 3
          : session.step === "position"
            ? 4
            : session.step === "connect"
              ? 5
              : isRoofColumnPanel
                ? 6
                : 5
      : session.step === "pick_panel"
        ? 2
        : session.step === "chord"
          ? 3
          : session.step === "profile"
            ? isRoofTiePanel
              ? 4
              : 3
            : session.step === "location"
              ? isRoofTiePanel
                ? 5
                : 4
              : 6;

  const totalSteps = isBracing
    ? 5
    : isColumn
      ? isRoofColumnPanel
        ? 6
        : 5
      : isRoofTiePanel
        ? 6
        : 4;

  const tieLocationOptions = isRoofTiePanel
    ? TIE_BEAM_TRUSS_LOCATION_OPTIONS
    : TIE_BEAM_LOCATION_OPTIONS;

  const columnPositionOptions = isRoofColumnPanel
    ? COLUMN_TRUSS_POSITION_OPTIONS
    : COLUMN_WALL_POSITION_OPTIONS;

  const applyProfileInput = () => {
    const value = profileInput.trim().toUpperCase();
    if (!value) return;
    if (isBracing) {
      setAddBracingProfile(value);
    } else if (isColumn) {
      setAddColumnProfile(value);
    } else {
      setAddTieBeamProfile(value);
    }
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
            Add {isBracing ? "bracing" : isColumn ? "column" : "tie beam"} · step {stepNum}/{totalSteps}
          </p>
          <p className="truncate text-sm font-medium">{stepTitle}</p>
          {session.panel ? (
            <p className="truncate text-xs text-muted-foreground">
              {session.panel.label}
              {isBracing && session.step === "scope"
                ? ` · ${session.braceCount} X${session.braceCount > 1 ? "s" : ""} · ${session.profile}`
                : isTie && session.step === "scope" && session.location
                  ? ` · ${TIE_BEAM_TRUSS_LOCATION_OPTIONS.find((o) => o.id === session.location)?.label ?? session.location} · ${session.profile}`
                  : isTie && session.step === "profile"
                  ? ""
                  : isBracing
                    ? " · Full X"
                    : ""}
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
          {isBracing
            ? "Hover a panel on side walls, gable ends, or roof slopes — they highlight blue. Click to select one bay."
            : isColumn
              ? "Hover a wall, gable, or roof bay between frames — they highlight amber. Click to select."
              : "Hover a wall, gable, or roof panel between truss frames. Click to select the tie bay."}
        </p>
      ) : null}

      {session.step === "profile" ? (
        <div>
          <p className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Common sections
          </p>
          {(isBracing
            ? quickBracingProfiles
            : isColumn
              ? quickColumnProfiles
              : quickTieProfiles
          ).map((profile) => (
            <OptionRow
              key={profile}
              label={profile}
              active={session.profile === profile}
              onClick={() =>
                isBracing
                  ? setAddBracingProfile(profile)
                  : isColumn
                    ? setAddColumnProfile(profile)
                    : setAddTieBeamProfile(profile)
              }
            />
          ))}
          <div className="space-y-2 border-t border-border/60 px-3 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Custom section
            </p>
            <p className="text-xs text-muted-foreground">
              {isBracing
                ? "Type any catalog designation (e.g. L80x80x8, SHS100x100x5)"
                : isColumn
                  ? "Type any catalog designation (e.g. HEA200, HEA240)"
                  : "Type any catalog designation (e.g. IPE200, IPE240)"}
            </p>
            <div className="flex gap-2">
              <Input
                value={profileInput}
                onChange={(e) => setProfileInput(e.target.value)}
                placeholder="Profile designation…"
                className="h-9 flex-1 text-sm"
                autoComplete="off"
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
        </div>
      ) : null}

      {isColumn && session.step === "position" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            {isRoofColumnPanel
              ? "Position under the truss from eave to ridge — column spans from ground to the selected connection."
              : "Position along the bay — column spans from ground to eave at the start frame, 33%, middle, 66%, or end frame."}
          </p>
          {columnPositionOptions.map((opt) => (
            <OptionRow
              key={opt.id}
              label={opt.label}
              detail={opt.detail}
              onClick={() => selectAddColumnPosition(opt.id)}
            />
          ))}
        </div>
      ) : null}

      {isColumn && session.step === "connect" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            Choose where the column top connects under the truss or rafter.
          </p>
          <OptionRow
            label="Automatic"
            detail="Connect to truss bottom chord when present, otherwise eave"
            onClick={() => setAddColumnConnect("auto")}
          />
          <OptionRow
            label="Truss bottom chord"
            detail="Top of column meets the truss BC at this X panel node"
            onClick={() => setAddColumnConnect("truss_bc")}
          />
          <OptionRow
            label="Eave level"
            detail="Top of column stops at eave beam height"
            onClick={() => setAddColumnConnect("eave")}
          />
        </div>
      ) : null}

      {isColumn && session.step === "scope" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            Choose how many bays get a column at the selected position.
          </p>
          {columnScopeOptions.map((opt) => (
            <OptionRow
              key={opt.id}
              label={opt.label}
              detail={opt.detail}
              onClick={() => void commitAddColumnScope(opt.id)}
            />
          ))}
        </div>
      ) : null}

      {isTie && session.step === "chord" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            Tie runs between truss frames along Z. Choose which chord to follow on
            the selected roof slope.
          </p>
          <OptionRow
            label="Top chord (TC)"
            detail="Along the sloped top chord between truss frames"
            onClick={() => setAddTieBeamChord("tc")}
          />
          <OptionRow
            label="Bottom chord (BC)"
            detail="Along the bottom chord at eave level"
            onClick={() => setAddTieBeamChord("bc")}
          />
          <OptionRow
            label="Both chords"
            detail="Place a tie on TC and BC at the same location"
            onClick={() => setAddTieBeamChord("both")}
          />
        </div>
      ) : null}

      {isTie && session.step === "location" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            {isRoofTiePanel
              ? "Position along the truss chord from eave to ridge — tie spans the full bay between truss frames."
              : "Choose height along the column — tie spans the full bay between columns at ground, 33%, middle, 66%, or eave level."}
          </p>
          {tieLocationOptions.map((opt) => (
            <OptionRow
              key={opt.id}
              label={opt.label}
              detail={opt.detail}
              onClick={() => selectAddTieBeamLocation(opt.id)}
            />
          ))}
        </div>
      ) : null}

      {isTie && session.step === "scope" ? (
        <div>
          <p className="px-3 pt-2 pb-1 text-xs leading-relaxed text-muted-foreground">
            Choose how many bays and slopes get a tie at the selected chord location.
          </p>
          {tieScopeOptions.map((opt) => (
            <OptionRow
              key={opt.id}
              label={opt.label}
              detail={opt.detail}
              onClick={() => void commitAddTieBeamScope(opt.id)}
            />
          ))}
        </div>
      ) : null}

      {isBracing && session.step === "brace_count" ? (
        <div className="space-y-3 px-3 py-3">
          <p className="text-xs leading-relaxed text-muted-foreground">
            Split tall walls, gable ends, or wide roof panels into stacked X-braces
            instead of one long diagonal.
          </p>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">X-braces per panel</span>
            <span className="tabular-nums text-sm font-semibold">{braceCountDraft}</span>
          </div>
          <input
            type="range"
            min={1}
            max={5}
            step={1}
            value={braceCountDraft}
            onChange={(e) => setBraceCountDraft(Number(e.target.value))}
            className="h-2 w-full cursor-pointer accent-primary"
            aria-label="X-braces per panel"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>1</span>
            <span>5</span>
          </div>
          <Button
            type="button"
            size="sm"
            className="h-9 w-full"
            onClick={() => setAddBracingBraceCount(braceCountDraft)}
          >
            Continue
          </Button>
        </div>
      ) : null}

      {isBracing && session.step === "scope" ? (
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

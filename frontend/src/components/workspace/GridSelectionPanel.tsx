"use client";

import { ChevronRight, Grid3X3, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  columnsInBay,
  midBayZLabel,
} from "@/lib/grid-selection";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { GridSelectionContext } from "@/types/grid-selection";

type ColumnPosition = "start" | "mid" | "end";

function ListRow({
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
        "flex w-full items-center justify-between gap-2 border-b border-border/60 px-3 py-3 text-left text-sm transition-colors",
        "hover:bg-muted/40",
        active && "bg-muted/50",
      )}
    >
      <span className="font-medium">{label}</span>
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {detail ? <span>{detail}</span> : null}
        <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-50" />
      </span>
    </button>
  );
}

type PanelSection = "add_column" | "add_tie" | null;

export function GridSelectionPanel({ context }: { context: GridSelectionContext }) {
  const {
    projectElements,
    busy,
    clearSelection,
    placeGridColumn,
    placeGridTieBeam,
  } = useProjectStore(
    useShallow((s) => ({
      projectElements: s.projectElements,
      busy: s.isLoading || s.isMacroLoading,
      clearSelection: s.clearSelection,
      placeGridColumn: s.placeGridColumn,
      placeGridTieBeam: s.placeGridTieBeam,
    })),
  );

  const [openSection, setOpenSection] = useState<PanelSection>(null);
  const [xAxis, setXAxis] = useState(context.xLabels[0] ?? "A");
  const [position, setPosition] = useState<ColumnPosition>("mid");
  const [columnProfile, setColumnProfile] = useState(context.defaultColumnProfile);
  const [tieProfile, setTieProfile] = useState(context.defaultTieProfile);
  const [tieXAxis, setTieXAxis] = useState(context.xLabels[0] ?? "A");

  const zForPosition = useMemo(() => {
    if (position === "start") return context.zStart;
    if (position === "end") return context.zEnd;
    return midBayZLabel(context.zStart, context.zEnd);
  }, [context.zEnd, context.zStart, position]);

  const bayColumns = useMemo(
    () =>
      columnsInBay(
        projectElements,
        context.zStart,
        context.zEnd,
        context.xLabels,
      ),
    [context.xLabels, context.zEnd, context.zStart, projectElements],
  );

  const toggle = (section: PanelSection) => {
    setOpenSection((prev) => (prev === section ? null : section));
  };

  const applyColumn = () => {
    void placeGridColumn(xAxis, zForPosition, columnProfile);
    setOpenSection(null);
  };

  const applyTie = () => {
    void placeGridTieBeam(tieXAxis, tieProfile, "eave");
    setOpenSection(null);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-border/60 px-3 py-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            <Grid3X3 className="h-3 w-3" />
            Grid bay
          </p>
          <p className="truncate text-sm font-medium">{context.label}</p>
          <p className="text-xs text-muted-foreground">{context.subtitle}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {bayColumns.length} column{bayColumns.length === 1 ? "" : "s"} in bay
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={clearSelection}
          aria-label="Clear selection"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ListRow
        label="Add column"
        detail={`${xAxis} · ${zForPosition}`}
        active={openSection === "add_column"}
        onClick={() => toggle("add_column")}
      />
      {openSection === "add_column" ? (
        <div className="space-y-3 border-b border-border/60 bg-background p-3">
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Grid line (X)
            </p>
            <div className="flex flex-wrap gap-1">
              {context.xLabels.map((label) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setXAxis(label)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs",
                    xAxis === label
                      ? "border-primary bg-primary/10 font-medium text-primary"
                      : "border-border hover:bg-muted/50",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Position along bay
            </p>
            <div className="flex flex-wrap gap-1">
              {(
                [
                  ["start", `Frame ${context.zStart}`],
                  ["mid", "Mid bay"],
                  ["end", `Frame ${context.zEnd}`],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setPosition(key)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs",
                    position === key
                      ? "border-primary bg-primary/10 font-medium text-primary"
                      : "border-border hover:bg-muted/50",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <Input
            value={columnProfile}
            onChange={(e) => setColumnProfile(e.target.value)}
            placeholder="Section e.g. HEA200"
            className="h-9 text-sm"
            disabled={busy}
          />
          <Button
            type="button"
            size="sm"
            className="w-full"
            disabled={busy || !columnProfile.trim()}
            onClick={applyColumn}
          >
            Place column at {xAxis} · {zForPosition}
          </Button>
        </div>
      ) : null}

      <ListRow
        label="Add tie beam"
        detail={`${tieXAxis} · eave`}
        active={openSection === "add_tie"}
        onClick={() => toggle("add_tie")}
      />
      {openSection === "add_tie" ? (
        <div className="space-y-3 border-b border-border/60 bg-background p-3">
          <p className="text-xs leading-relaxed text-muted-foreground">
            Longitudinal tie between frame {context.zStart} and {context.zEnd}{" "}
            at eave level.
          </p>
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Grid line (X)
            </p>
            <div className="flex flex-wrap gap-1">
              {context.xLabels.map((label) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setTieXAxis(label)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs",
                    tieXAxis === label
                      ? "border-primary bg-primary/10 font-medium text-primary"
                      : "border-border hover:bg-muted/50",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <Input
            value={tieProfile}
            onChange={(e) => setTieProfile(e.target.value)}
            placeholder="Section e.g. IPE200"
            className="h-9 text-sm"
            disabled={busy}
          />
          <Button
            type="button"
            size="sm"
            className="w-full"
            disabled={busy || !tieProfile.trim()}
            onClick={applyTie}
          >
            Place tie beam
          </Button>
        </div>
      ) : null}
    </div>
  );
}

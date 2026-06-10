"use client";

import { ChevronRight, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  COLUMN_SCOPE_OPTIONS,
  describeColumnScopeCount,
  type ColumnScopeChoice,
} from "@/lib/column-member-scope";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { SelectionContext } from "@/types/interaction";
import type { ElementAlignment, ElementRotation } from "@/types/project";

const ROTATIONS: ElementRotation[] = [0, 90, 180, 270];
const ALIGNMENTS: ElementAlignment[] = ["top", "center", "bottom"];

type PanelSection =
  | "section_size"
  | "rotation"
  | "alignment"
  | "location"
  | "remove";

type ColumnSelectionPanelProps = {
  context: SelectionContext;
};

function ListRow({
  label,
  detail,
  active,
  onClick,
  destructive,
}: {
  label: string;
  detail?: string;
  active?: boolean;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between gap-2 border-b border-border/60 px-3 py-3 text-left text-sm transition-colors",
        "hover:bg-muted/40",
        active && "bg-muted/50",
        destructive && "text-red-600 hover:bg-red-50/80",
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

function ScopePicker({
  value,
  onChange,
}: {
  value: ColumnScopeChoice;
  onChange: (scope: ColumnScopeChoice) => void;
}) {
  return (
    <div className="border-b border-border/40 bg-muted/20">
      {COLUMN_SCOPE_OPTIONS.map((opt) => (
        <button
          key={opt.scope}
          type="button"
          onClick={() => onChange(opt.scope)}
          className={cn(
            "flex w-full items-center px-3 py-2.5 text-left text-sm",
            value === opt.scope
              ? "bg-primary/10 font-medium text-primary"
              : "text-foreground hover:bg-muted/50",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function ColumnSelectionPanel({ context }: ColumnSelectionPanelProps) {
  const {
    element,
    projectElements,
    busy,
    clearSelection,
    applyColumnProfile,
    applyColumnRotation,
    applyColumnAlignment,
    deleteColumnsScoped,
    startMemberPickMode,
  } = useProjectStore(
    useShallow((s) => ({
      element:
        s.projectElements.find((e) => e.id === context.elementId) ?? null,
      projectElements: s.projectElements,
      busy: s.isLoading || s.isMacroLoading,
      clearSelection: s.clearSelection,
      applyColumnProfile: s.applyColumnProfile,
      applyColumnRotation: s.applyColumnRotation,
      applyColumnAlignment: s.applyColumnAlignment,
      deleteColumnsScoped: s.deleteColumnsScoped,
      startMemberPickMode: s.startMemberPickMode,
    })),
  );

  const [openSection, setOpenSection] = useState<PanelSection | null>(null);
  const [scope, setScope] = useState<ColumnScopeChoice>("selection");
  const [profileInput, setProfileInput] = useState("");
  const [removeConfirmed, setRemoveConfirmed] = useState(false);

  const removeCount = useMemo(() => {
    if (scope === "pick_members") return 0;
    return describeColumnScopeCount(
      projectElements,
      context.elementId,
      scope,
    );
  }, [projectElements, context.elementId, scope]);

  if (!element) {
    return null;
  }

  const toggleSection = (section: PanelSection) => {
    setOpenSection((prev) => (prev === section ? null : section));
    setRemoveConfirmed(false);
  };

  const applyProfile = async () => {
    const profile = profileInput.trim().toUpperCase();
    if (!profile) return;
    if (scope === "pick_members") {
      startMemberPickMode({ intent: "profile", profile });
      return;
    }
    try {
      await applyColumnProfile(profile, scope);
      setProfileInput("");
    } catch {
      // Error surfaced via store.statuses / store.error
    }
  };

  const applyRotation = async (rotation: ElementRotation) => {
    if (scope === "pick_members") {
      startMemberPickMode({ intent: "rotation", rotation });
      return;
    }
    await applyColumnRotation(rotation, scope);
  };

  const applyAlignment = async (alignment: ElementAlignment) => {
    if (scope === "pick_members") {
      startMemberPickMode({ intent: "alignment", alignment });
      return;
    }
    await applyColumnAlignment(alignment, scope);
  };

  const handleRemove = async () => {
    if (scope === "pick_members") {
      startMemberPickMode({ intent: "delete" });
      return;
    }
    if (!removeConfirmed) {
      setRemoveConfirmed(true);
      return;
    }
    await deleteColumnsScoped(scope);
    setRemoveConfirmed(false);
    setOpenSection(null);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-border/60 px-3 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Column
          </p>
          <p className="truncate text-sm font-medium">{context.label}</p>
          {context.locationSubtitle ? (
            <p className="text-xs text-muted-foreground">
              {context.locationSubtitle}
            </p>
          ) : null}
          {element.profile_name ? (
            <p className="text-xs text-muted-foreground">
              {element.profile_name}
            </p>
          ) : null}
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
        label="Section size"
        detail={element.profile_name ?? undefined}
        active={openSection === "section_size"}
        onClick={() => toggleSection("section_size")}
      />
      {openSection === "section_size" ? (
        <div className="border-b border-border/60 bg-background">
          <ScopePicker value={scope} onChange={setScope} />
          <div className="space-y-2 p-3">
            <Input
              value={profileInput}
              onChange={(e) => setProfileInput(e.target.value)}
              placeholder="Type section e.g. HEA400"
              className="h-9 text-sm"
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter") void applyProfile();
              }}
            />
            <Button
              type="button"
              size="sm"
              className="w-full"
              disabled={busy || !profileInput.trim()}
              onClick={() => void applyProfile()}
            >
              {scope === "pick_members" ? "Pick in viewport" : "Apply section"}
            </Button>
          </div>
        </div>
      ) : null}

      <ListRow
        label="Rotation"
        detail={`${element.rotation ?? 0}°`}
        active={openSection === "rotation"}
        onClick={() => toggleSection("rotation")}
      />
      {openSection === "rotation" ? (
        <div className="border-b border-border/60 bg-background">
          <ScopePicker value={scope} onChange={setScope} />
          <div className="divide-y divide-border/40">
            {ROTATIONS.map((deg) => (
              <button
                key={deg}
                type="button"
                disabled={busy}
                onClick={() => void applyRotation(deg)}
                className={cn(
                  "flex w-full px-3 py-2.5 text-left text-sm hover:bg-muted/50",
                  (element.rotation ?? 0) === deg && "bg-primary/5 font-medium",
                )}
              >
                {deg}°
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <ListRow
        label="Alignment"
        detail={element.alignment ?? "center"}
        active={openSection === "alignment"}
        onClick={() => toggleSection("alignment")}
      />
      {openSection === "alignment" ? (
        <div className="border-b border-border/60 bg-background">
          <ScopePicker value={scope} onChange={setScope} />
          <div className="divide-y divide-border/40">
            {ALIGNMENTS.map((align) => (
              <button
                key={align}
                type="button"
                disabled={busy}
                onClick={() => void applyAlignment(align)}
                className={cn(
                  "flex w-full px-3 py-2.5 text-left text-sm capitalize hover:bg-muted/50",
                  (element.alignment ?? "center") === align &&
                    "bg-primary/5 font-medium",
                )}
              >
                {align}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <ListRow
        label="Location"
        detail={context.gridX ?? undefined}
        active={openSection === "location"}
        onClick={() => toggleSection("location")}
      />
      {openSection === "location" ? (
        <div className="space-y-2 border-b border-border/60 bg-muted/10 p-3 text-xs">
          <div className="flex justify-between gap-2">
            <span className="text-muted-foreground">Frame</span>
            <span className="font-medium">{context.locationSubtitle || "—"}</span>
          </div>
          {context.gridX ? (
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Grid line</span>
              <span className="font-medium">{context.gridX}</span>
            </div>
          ) : null}
          <div className="flex justify-between gap-2">
            <span className="text-muted-foreground">Position (mm)</span>
            <span className="font-mono text-[11px]">
              {Math.round(element.position_mm.x)},{" "}
              {Math.round(element.position_mm.y)},{" "}
              {Math.round(element.position_mm.z)}
            </span>
          </div>
          <div className="flex justify-between gap-2">
            <span className="text-muted-foreground">Length</span>
            <span className="font-medium">
              {Math.round(element.length_mm)} mm
            </span>
          </div>
          <div className="break-all font-mono text-[10px] text-muted-foreground">
            {element.id}
          </div>
        </div>
      ) : null}

      <ListRow
        label="Remove"
        active={openSection === "remove"}
        onClick={() => toggleSection("remove")}
        destructive
      />
      {openSection === "remove" ? (
        <div className="border-b border-border/60 bg-background p-3">
          <ScopePicker value={scope} onChange={setScope} />
          {scope !== "pick_members" && removeConfirmed ? (
            <p className="mb-2 text-xs leading-relaxed text-red-700">
              Delete {removeCount} column{removeCount === 1 ? "" : "s"}? This
              cannot be undone.
            </p>
          ) : scope !== "pick_members" ? (
            <p className="mb-2 text-xs text-muted-foreground">
              {removeCount} column{removeCount === 1 ? "" : "s"} will be
              removed.
            </p>
          ) : null}
          <Button
            type="button"
            size="sm"
            className="w-full bg-red-600 text-white hover:bg-red-700"
            disabled={busy}
            onClick={() => void handleRemove()}
          >
            {scope === "pick_members"
              ? "Pick in viewport to remove"
              : removeConfirmed
                ? "Confirm delete"
                : "Delete"}
          </Button>
          {removeConfirmed ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2 w-full"
              onClick={() => setRemoveConfirmed(false)}
            >
              Cancel
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

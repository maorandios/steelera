"use client";

import { ChevronDown, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  actionsByTier,
  actionsForSelection,
  profileOptionsForContext,
  profileScopeOptions,
  trussTypeOptions,
} from "@/lib/interaction-actions";
import { cn } from "@/lib/utils";
import { useProjectStore, useSelectedElement } from "@/store/project-store";
import type { ProfileScope, SelectionActionId } from "@/types/interaction";
import type { TrussType } from "@/types/shed-config";

export function SelectionActionBar() {
  const selected = useSelectedElement();
  const selectionContext = useProjectStore((s) => s.selectionContext);
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const placementIntent = useProjectStore((s) => s.placementIntent);
  const pickedNodes = useProjectStore((s) => s.pickedNodes);
  const clearSelection = useProjectStore((s) => s.clearSelection);
  const cancelNodePlacement = useProjectStore((s) => s.cancelNodePlacement);
  const cancelGridPlacement = useProjectStore((s) => s.cancelGridPlacement);
  const startNodePlacement = useProjectStore((s) => s.startNodePlacement);
  const startFramePlacement = useProjectStore((s) => s.startFramePlacement);
  const updateMemberProfile = useProjectStore((s) => s.updateMemberProfile);
  const deleteSelectedMembers = useProjectStore((s) => s.deleteSelectedMembers);
  const changeTrussType = useProjectStore((s) => s.changeTrussType);
  const switchFramePrimary = useProjectStore((s) => s.switchFramePrimary);
  const removeSelectedFrame = useProjectStore((s) => s.removeSelectedFrame);
  const isLoading = useProjectStore((s) => s.isLoading);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const busy = isLoading || isMacroLoading;

  const [profileMenu, setProfileMenu] = useState(false);
  const [profileScope, setProfileScope] = useState<ProfileScope | null>(null);
  const [trussMenu, setTrussMenu] = useState(false);
  const [showMore, setShowMore] = useState(false);

  if (viewportMode === "pick_nodes") {
    const needed = placementIntent === "full_x" ? 4 : 2;
    return (
      <div className="mb-3 rounded-xl border border-blue-200/80 bg-blue-50/90 px-3 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-blue-900">Placement mode</p>
            <p className="mt-1 text-xs leading-relaxed text-blue-800/90">
              Click blue nodes to place{" "}
              {placementIntent === "full_x" ? "an X-brace" : "a brace"} (
              {pickedNodes.length}/{needed} picked).
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0"
            onClick={cancelNodePlacement}
            aria-label="Cancel placement"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  if (viewportMode === "pick_grid") {
    return (
      <div className="mb-3 rounded-xl border border-emerald-200/80 bg-emerald-50/90 px-3 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-emerald-900">Add frame</p>
            <p className="mt-1 text-xs leading-relaxed text-emerald-800/90">
              Click a numbered frame line along the length to insert a new portal
              frame with the same spacing.
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0"
            onClick={cancelGridPlacement}
            aria-label="Cancel"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  if (!selected || !selectionContext) return null;

  const actions = actionsForSelection(selectionContext);
  const tiers = actionsByTier(actions);
  const scopeOptions = profileScopeOptions(selectionContext);
  const profiles = profileOptionsForContext(selectionContext);
  const defaultScope =
    profileScope ?? selectionContext.defaultProfileScope;

  const openProfileMenu = () => {
    setProfileScope(selectionContext.defaultProfileScope);
    setProfileMenu(true);
    setTrussMenu(false);
  };

  const run = async (id: SelectionActionId) => {
    switch (id) {
      case "change_profile":
        openProfileMenu();
        return;
      case "change_truss_type":
        setTrussMenu(true);
        setProfileMenu(false);
        return;
      case "switch_to_truss":
        await switchFramePrimary("truss");
        return;
      case "switch_to_rafter":
        await switchFramePrimary("rafter");
        return;
      case "add_frame_like_this":
        startFramePlacement();
        return;
      case "delete_pair":
        await deleteSelectedMembers(
          selectionContext.pairId ? "pair" : "selection",
        );
        return;
      case "delete_frame":
        await removeSelectedFrame();
        return;
      case "more_remove":
        await deleteSelectedMembers("selection");
        return;
      case "add_brace_here":
        await startNodePlacement("single_brace");
        return;
      case "add_x_brace":
        await startNodePlacement("full_x");
        return;
      default:
        return;
    }
  };

  const renderChip = (id: SelectionActionId, label: string) => (
    <button
      key={id}
      type="button"
      disabled={busy}
      onClick={() => void run(id)}
      className={cn(
        "rounded-full border border-border/80 bg-background px-3 py-1.5 text-xs",
        "transition-colors hover:border-primary/40 hover:bg-primary/5",
        busy && "opacity-50",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="mb-3 space-y-2 rounded-xl border border-border/80 bg-muted/30 px-3 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Selected
          </p>
          <p className="truncate text-sm font-medium text-foreground">
            {selectionContext.label}
          </p>
          {selectionContext.locationSubtitle ? (
            <p className="text-xs text-muted-foreground">
              {selectionContext.locationSubtitle}
            </p>
          ) : null}
          {selectionContext.profile ? (
            <p className="text-xs text-muted-foreground">
              {selectionContext.profile}
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

      {tiers.primary.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {tiers.primary.map((action) =>
            renderChip(action.id, action.label),
          )}
        </div>
      ) : null}

      {tiers.structure.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {tiers.structure.map((action) =>
            renderChip(action.id, action.label),
          )}
        </div>
      ) : null}

      {(tiers.more.length > 0 || tiers.structure.length > 0) && (
        <button
          type="button"
          className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
          onClick={() => setShowMore((v) => !v)}
        >
          <ChevronDown
            className={cn("h-3.5 w-3.5 transition-transform", showMore && "rotate-180")}
          />
          {showMore ? "Less" : "More options"}
        </button>
      )}

      {showMore && tiers.more.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {tiers.more.map((action) => renderChip(action.id, action.label))}
        </div>
      ) : null}

      {profileMenu ? (
        <div className="rounded-lg border border-border/60 bg-background p-2 space-y-2">
          {scopeOptions.length > 1 ? (
            <div className="flex flex-wrap gap-1">
              {scopeOptions.map((opt) => (
                <button
                  key={opt.scope}
                  type="button"
                  onClick={() => setProfileScope(opt.scope)}
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[11px]",
                    defaultScope === opt.scope
                      ? "bg-primary/15 text-primary"
                      : "bg-muted text-muted-foreground hover:bg-muted/80",
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          ) : null}
          <p className="text-xs text-muted-foreground">Pick a section profile</p>
          <div className="flex flex-wrap gap-1.5">
            {profiles.map((profile) => (
              <button
                key={profile}
                type="button"
                disabled={busy}
                onClick={() => {
                  void updateMemberProfile(profile, defaultScope).then(() => {
                    setProfileMenu(false);
                    setProfileScope(null);
                  });
                }}
                className="rounded-full bg-muted px-2.5 py-1 text-xs hover:bg-primary/10"
              >
                {profile}
              </button>
            ))}
            <button
              type="button"
              className="rounded-full px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted"
              onClick={() => {
                setProfileMenu(false);
                setProfileScope(null);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {trussMenu ? (
        <div className="rounded-lg border border-border/60 bg-background p-2 space-y-2">
          <p className="text-xs text-muted-foreground">Truss pattern</p>
          <div className="flex flex-wrap gap-1.5">
            {trussTypeOptions().map((opt) => (
              <button
                key={opt.value}
                type="button"
                disabled={busy}
                onClick={() => {
                  void changeTrussType(
                    opt.value as Exclude<TrussType, "none">,
                    "frame",
                  ).then(() => setTrussMenu(false));
                }}
                className="rounded-full bg-muted px-2.5 py-1 text-xs hover:bg-primary/10"
              >
                {opt.label}
              </button>
            ))}
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                void changeTrussType(
                  (selectionContext.trussType ?? "pratt") as Exclude<
                    TrussType,
                    "none"
                  >,
                  "all",
                ).then(() => setTrussMenu(false));
              }}
              className="rounded-full border border-dashed border-border px-2.5 py-1 text-xs hover:bg-muted"
            >
              Apply to all frames
            </button>
            <button
              type="button"
              className="rounded-full px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted"
              onClick={() => setTrussMenu(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

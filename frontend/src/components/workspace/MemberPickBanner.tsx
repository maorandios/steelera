"use client";

import { Button } from "@/components/ui/button";
import { useProjectStore } from "@/store/project-store";

export function MemberPickBanner() {
  const pick = useProjectStore((s) => s.memberPickMode);
  const finishMemberPickMode = useProjectStore((s) => s.finishMemberPickMode);
  const cancelMemberPickMode = useProjectStore((s) => s.cancelMemberPickMode);

  if (!pick) return null;

  const actionLabel =
    pick.intent === "profile"
      ? `Apply ${pick.profile}`
      : pick.intent === "rotation"
        ? `Rotation ${pick.rotation}°`
        : pick.intent === "alignment"
          ? `Alignment ${pick.alignment}`
          : "Remove";

  return (
    <div className="rounded-xl border border-violet-200/80 bg-violet-50/95 px-3 py-3">
      <p className="text-xs font-semibold text-violet-900">
        Pick columns · {actionLabel}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-violet-800/90">
        {pick.intent === "delete"
          ? "Each click removes one column. Done only exits pick mode."
          : "Click columns in the viewport."}
        {pick.updatedCount > 0
          ? ` ${pick.updatedCount} ${pick.intent === "delete" ? "removed" : "updated"} so far.`
          : pick.intent === "delete"
            ? " None removed yet."
            : " None yet."}
      </p>
      <div className="mt-2 flex gap-2">
        <Button
          type="button"
          size="sm"
          className="h-8"
          onClick={finishMemberPickMode}
        >
          Done
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8"
          onClick={cancelMemberPickMode}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}

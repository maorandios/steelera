"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CUSTOM_VALUE } from "@/lib/onboarding-flow";
import { useProjectStore } from "@/store/project-store";
import type { QuickRepliesPayload } from "@/types/chat";

type QuickRepliesProps = {
  payload: QuickRepliesPayload;
  active: boolean;
};

export function QuickReplies({ payload, active }: QuickRepliesProps) {
  const answerOnboarding = useProjectStore((s) => s.answerOnboarding);
  const isProposing = useProjectStore((s) => s.isProposing);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const disabled = !active || isProposing || isMacroLoading;

  const options = [
    ...payload.options,
    ...(payload.allowCustom &&
    !payload.options.some((o) => o.value === CUSTOM_VALUE)
      ? [{ label: "Custom…", value: CUSTOM_VALUE }]
      : []),
  ];

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {options.map((option) => (
        <Button
          key={option.value}
          type="button"
          variant="secondary"
          size="sm"
          disabled={disabled}
          className={cn(
            "h-auto min-h-9 whitespace-normal rounded-full px-4 py-2 text-left text-sm font-normal",
            !disabled && "hover:bg-primary/10 hover:text-primary",
          )}
          onClick={() => answerOnboarding(option.value)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}

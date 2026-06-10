"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  extractPendingProfileFromMessages,
  profileChoiceMessage,
  WORKSPACE_CUSTOM_PROFILE,
  WORKSPACE_PICK_ON_MODEL,
} from "@/lib/pending-profile";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { WorkspaceQuickRepliesPayload } from "@/types/chat";

type WorkspaceQuickRepliesProps = {
  payload: WorkspaceQuickRepliesPayload;
  active: boolean;
};

function CustomProfileInput({
  placeholder,
  disabled,
  onSubmit,
  onCancel,
}: {
  placeholder: string;
  disabled: boolean;
  onSubmit: (profile: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/70 bg-background p-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="h-9 min-w-[10rem] flex-1 text-sm"
        autoFocus
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          }
          if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
          }
        }}
      />
      <Button
        type="button"
        size="sm"
        disabled={disabled || !value.trim()}
        onClick={submit}
      >
        Apply
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        disabled={disabled}
        onClick={onCancel}
      >
        Cancel
      </Button>
    </div>
  );
}

export function WorkspaceQuickReplies({
  payload,
  active,
}: WorkspaceQuickRepliesProps) {
  const sendMessage = useProjectStore((s) => s.sendMessage);
  const startProfilePickMode = useProjectStore((s) => s.startProfilePickMode);
  const messages = useProjectStore((s) => s.messages);
  const isLoading = useProjectStore((s) => s.isLoading);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const disabled = !active || isLoading || isMacroLoading;
  const [customOpen, setCustomOpen] = useState(false);

  const options = [
    ...payload.options.filter((o) => o.value !== WORKSPACE_CUSTOM_PROFILE),
    ...(payload.allowCustom
      ? [{ label: "Other size…", value: WORKSPACE_CUSTOM_PROFILE }]
      : []),
  ];

  const handleOption = (value: string) => {
    if (value === WORKSPACE_CUSTOM_PROFILE) {
      setCustomOpen(true);
      return;
    }
    if (value === WORKSPACE_PICK_ON_MODEL) {
      const profile = extractPendingProfileFromMessages(messages);
      if (profile) {
        startProfilePickMode(profile);
      }
      return;
    }
    void sendMessage(value);
  };

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <Button
            key={option.value}
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled || customOpen}
            className={cn(
              "h-auto min-h-9 whitespace-normal rounded-full px-4 py-2 text-left text-sm font-normal",
              !disabled && "hover:bg-primary/10 hover:text-primary",
              option.value === WORKSPACE_CUSTOM_PROFILE &&
                customOpen &&
                "border-primary/40 bg-primary/10 text-primary",
            )}
            onClick={() => handleOption(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </div>
      {customOpen && payload.allowCustom ? (
        <CustomProfileInput
          placeholder={
            payload.customPlaceholder ?? "Type any section e.g. HEA380"
          }
          disabled={disabled}
          onSubmit={(profile) => {
            setCustomOpen(false);
            void sendMessage(profileChoiceMessage(profile));
          }}
          onCancel={() => setCustomOpen(false)}
        />
      ) : null}
      {active && !customOpen ? (
        <p className="text-[11px] text-muted-foreground">
          {payload.allowCustom
            ? "Tap an option or choose Other size…"
            : "Or type your answer in the field below."}
        </p>
      ) : null}
    </div>
  );
}

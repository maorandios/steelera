"use client";

import { MousePointerClick, Send } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatStatus } from "@/components/chat/ChatStatus";
import { SelectionActionBar } from "@/components/chat/SelectionActionBar";
import { ColumnSelectionPanel } from "@/components/workspace/ColumnSelectionPanel";
import { GridSelectionPanel } from "@/components/workspace/GridSelectionPanel";
import { MemberPickBanner } from "@/components/workspace/MemberPickBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useProjectStore, useSelectedElement } from "@/store/project-store";

function WorkspaceEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <MousePointerClick className="h-10 w-10 text-muted-foreground/50" />
      <div>
        <p className="text-sm font-medium text-foreground">
          Click a member or grid bay
        </p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          Select steel to edit members, or click between frames to add columns
          and tie beams.
        </p>
      </div>
    </div>
  );
}

export function WorkspaceInteractionPanel() {
  const messages = useProjectStore((s) => s.messages);
  const statuses = useProjectStore((s) => s.statuses);
  const isLoading = useProjectStore((s) => s.isLoading);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const sendMessage = useProjectStore((s) => s.sendMessage);
  const selectedElementId = useProjectStore((s) => s.selectedElementId);
  const selectionContext = useProjectStore((s) => s.selectionContext);
  const gridSelectionContext = useProjectStore((s) => s.gridSelectionContext);
  const viewportMode = useProjectStore((s) => s.viewportMode);
  const memberPickMode = useProjectStore((s) => s.memberPickMode);
  const storeError = useProjectStore((s) => s.error);
  const clearError = useProjectStore((s) => s.clearError);
  const selected = useSelectedElement();

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const inSpecialMode =
    viewportMode !== "inspect" || memberPickMode !== null;
  const isColumn =
    selectionContext?.elementType === "column" && selected && !memberPickMode;
  const showGridSelection =
    Boolean(gridSelectionContext) && !memberPickMode && !inSpecialMode;
  const showGenericSelection =
    Boolean(selectedElementId && selectionContext && !isColumn && !memberPickMode) ||
    (inSpecialMode && !memberPickMode && viewportMode !== "pick_members_profile");

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, statuses, selectedElementId, scrollToBottom]);

  const handleAdviceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value) return;
    setInput("");
    await sendMessage(value);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain"
      >
        <div className="flex flex-col gap-3 p-4">
          {memberPickMode ? <MemberPickBanner /> : null}

          {showGridSelection && gridSelectionContext ? (
            <GridSelectionPanel
              key={gridSelectionContext.gridId}
              context={gridSelectionContext}
            />
          ) : isColumn && selectionContext ? (
            <ColumnSelectionPanel
              key={selectionContext.elementId}
              context={selectionContext}
            />
          ) : showGenericSelection ? (
            <SelectionActionBar layout="panel" />
          ) : !memberPickMode && !showGridSelection ? (
            <WorkspaceEmptyState />
          ) : null}

          {messages.length > 0 ? (
            <div className="space-y-2 border-t border-border/60 pt-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Advice
              </p>
              {messages.map((msg, i) => (
                <ChatMessage
                  key={`${msg.role}-${i}-${msg.content.slice(0, 12)}`}
                  message={msg}
                  actionsActive={false}
                  variant="default"
                />
              ))}
            </div>
          ) : null}

          <ChatStatus
            statuses={statuses}
            isLoading={isLoading || isMacroLoading}
          />
        </div>
      </div>

      <form
        onSubmit={handleAdviceSubmit}
        className="shrink-0 border-t border-border bg-background p-4"
      >
        {storeError ? (
          <p className="mb-2 text-xs text-red-600" role="alert">
            {storeError}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => {
              clearError();
              setInput(e.target.value);
            }}
            placeholder="Ask for engineering advice…"
            disabled={isLoading || isMacroLoading}
            className="h-10 flex-1 bg-card text-sm"
            autoComplete="off"
          />
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || isMacroLoading || !input.trim()}
            className="h-10 w-10 shrink-0"
          >
            <Send className="h-4 w-4" />
            <span className="sr-only">Send</span>
          </Button>
        </div>
      </form>
    </div>
  );
}

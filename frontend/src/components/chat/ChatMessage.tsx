"use client";

import { ChatProposalBlock } from "@/components/chat/ChatProposalBlock";
import { LocationPicker } from "@/components/chat/LocationPicker";
import { QuickReplies } from "@/components/chat/QuickReplies";
import { SiteMapPinPicker } from "@/components/chat/SiteMapPinPicker";
import { SiteRefinePicker } from "@/components/chat/SiteRefinePicker";
import { ShedComponentChecklist } from "@/components/chat/ShedComponentChecklist";
import { ViewportPickPrompt } from "@/components/chat/ViewportPickPrompt";
import { WorkspaceQuickReplies } from "@/components/chat/WorkspaceQuickReplies";
import { inferWorkspaceQuickReplies } from "@/lib/infer-workspace-replies";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
  actionsActive?: boolean;
  variant?: "default" | "onboarding";
}

export function ChatMessage({
  message,
  actionsActive = false,
  variant = "default",
}: ChatMessageProps) {
  const isOnboarding = variant === "onboarding";
  const isUser = message.role === "user";
  const block = !isUser ? message.ui_block : null;
  const checklist =
    block?.type === "show_component_checklist" ? block.payload : null;
  const quickReplies =
    block?.type === "quick_replies" ? block.payload : null;
  const workspaceQuickReplies =
    block?.type === "workspace_quick_replies"
      ? block.payload
      : !isUser && !isOnboarding && !block
        ? inferWorkspaceQuickReplies(message.content)
        : null;
  const viewportNodePick =
    block?.type === "viewport_node_pick" ? block.payload : null;
  const viewportGridPick =
    block?.type === "viewport_grid_pick" ? block.payload : null;
  const showProposal = block?.type === "show_proposal";
  const locationPicker = block?.type === "location_picker";
  const siteRefine = block?.type === "site_refine";
  const mapPin =
    block?.type === "map_pin_picker" ? block.payload : null;
  const hasInteractiveBlock = Boolean(
    checklist ||
      quickReplies ||
      workspaceQuickReplies ||
      viewportNodePick ||
      viewportGridPick ||
      showProposal ||
      locationPicker ||
      siteRefine ||
      mapPin,
  );
  const hideEmptyAssistant =
    isOnboarding &&
    !isUser &&
    !message.content.trim() &&
    locationPicker;

  if (hideEmptyAssistant) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[92%] text-sm leading-relaxed",
          isOnboarding ? "rounded-2xl px-1 py-1" : "rounded-2xl px-3.5 py-2.5",
          isUser
            ? isOnboarding
              ? "rounded-2xl bg-blue-600 px-4 py-2.5 text-white"
              : "bg-primary text-primary-foreground"
            : isOnboarding
              ? "max-w-full w-full text-slate-700"
              : "border border-border bg-card text-card-foreground",
          hasInteractiveBlock && "max-w-full w-full",
        )}
      >
        {!isUser && !isOnboarding ? (
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Steelera AI
          </p>
        ) : null}
        {message.content.trim() && !workspaceQuickReplies ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : workspaceQuickReplies?.question ? (
          <p className="whitespace-pre-wrap">{workspaceQuickReplies.question}</p>
        ) : message.content.trim() ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : null}
        {locationPicker ? <LocationPicker active={actionsActive} /> : null}
        {siteRefine ? <SiteRefinePicker active={actionsActive} /> : null}
        {mapPin ? (
          <SiteMapPinPicker
            initialLat={mapPin.latitude}
            initialLon={mapPin.longitude}
            active={actionsActive}
          />
        ) : null}
        {quickReplies ? (
          <QuickReplies payload={quickReplies} active={actionsActive} />
        ) : null}
        {workspaceQuickReplies ? (
          <WorkspaceQuickReplies
            payload={workspaceQuickReplies}
            active={actionsActive}
          />
        ) : null}
        {viewportNodePick ? (
          <ViewportPickPrompt
            variant="node"
            payload={viewportNodePick}
            active={actionsActive}
          />
        ) : null}
        {viewportGridPick ? (
          <ViewportPickPrompt
            variant="grid"
            payload={viewportGridPick}
            active={actionsActive}
          />
        ) : null}
        {showProposal ? <ChatProposalBlock active={actionsActive} /> : null}
        {checklist ? <ShedComponentChecklist payload={checklist} /> : null}
      </div>
    </div>
  );
}

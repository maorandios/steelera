"use client";

import { useEffect, useRef } from "react";

import { useProjectStore } from "@/store/project-store";
import type {
  ViewportGridPickPayload,
  ViewportNodePickPayload,
} from "@/types/chat";

type ViewportPickPromptProps = {
  variant: "node" | "grid";
  payload: ViewportNodePickPayload | ViewportGridPickPayload;
  active: boolean;
};

export function ViewportPickPrompt({
  variant,
  payload,
  active,
}: ViewportPickPromptProps) {
  const startedRef = useRef(false);
  const startNodePlacement = useProjectStore((s) => s.startNodePlacement);
  const startFramePlacement = useProjectStore((s) => s.startFramePlacement);
  const viewportMode = useProjectStore((s) => s.viewportMode);

  useEffect(() => {
    if (!active || startedRef.current) return;
    startedRef.current = true;

    if (variant === "node") {
      const nodePayload = payload as ViewportNodePickPayload;
      void startNodePlacement(nodePayload.intent, {
        profile: nodePayload.profile ?? undefined,
      });
      return;
    }

    startFramePlacement();
  }, [active, variant, payload, startNodePlacement, startFramePlacement]);

  const inPickMode =
    viewportMode === (variant === "node" ? "pick_nodes" : "pick_grid");

  return (
    <p className="mt-2 text-xs text-muted-foreground">
      {inPickMode
        ? "Pick points in the 3D viewport — see the banner above the chat input."
        : "Opening placement mode in the viewport…"}
    </p>
  );
}

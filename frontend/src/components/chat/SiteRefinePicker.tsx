"use client";

import { Building2, Factory, MapPinned } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { isSiteClimatePending } from "@/lib/placeholder-site";
import {
  SITE_BUILT_UP,
  SITE_OPEN_INDUSTRIAL,
  SITE_PIN,
} from "@/lib/site-surroundings";
import { useProjectStore } from "@/store/project-store";

type SiteRefinePickerProps = {
  active: boolean;
};

export function SiteRefinePicker({ active }: SiteRefinePickerProps) {
  const confirmSiteRefine = useProjectStore((s) => s.confirmSiteRefine);
  const isProposing = useProjectStore((s) => s.isProposing);
  const siteContext = useProjectStore((s) => s.siteContext);
  const disabled = !active || isProposing;
  const alreadyOpen =
    !isSiteClimatePending(siteContext) && siteContext?.exposure === "open";

  return (
    <div className="mt-3 flex flex-col gap-2">
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={disabled}
        className={cn(
          "h-auto min-h-9 justify-start gap-2 rounded-full px-4 py-2 text-left text-sm font-normal",
          !disabled && "hover:bg-primary/10 hover:text-primary",
        )}
        onClick={() => confirmSiteRefine(SITE_BUILT_UP)}
      >
        <Building2 className="h-4 w-4 shrink-0" />
        Built-up / inside city — looks right
      </Button>
      {!alreadyOpen ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={disabled}
          className={cn(
            "h-auto min-h-9 justify-start gap-2 rounded-full px-4 py-2 text-left text-sm font-normal",
            !disabled && "hover:bg-primary/10 hover:text-primary",
          )}
          onClick={() => confirmSiteRefine(SITE_OPEN_INDUSTRIAL)}
        >
          <Factory className="h-4 w-4 shrink-0" />
          Open or industrial land
        </Button>
      ) : null}
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={disabled}
        className="h-auto min-h-9 justify-start gap-2 rounded-full px-4 py-2 text-sm font-normal"
        onClick={() => confirmSiteRefine(SITE_PIN)}
      >
        <MapPinned className="h-4 w-4 shrink-0" />
        Pin exact site on map
      </Button>
    </div>
  );
}

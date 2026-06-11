"use client";

import {
  ArrowLeft,
  Building2,
  ChevronRight,
  Factory,
  Loader2,
  MapPinned,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ChatProposalBlock } from "@/components/chat/ChatProposalBlock";
import { SiteMapPinPicker } from "@/components/chat/SiteMapPinPicker";
import { OnboardingLoader } from "@/components/onboarding/OnboardingLoader";
import { SteeleraMark } from "@/components/onboarding/SteeleraMark";
import { isSiteClimatePending } from "@/lib/placeholder-site";
import {
  formatClimateLine,
  formatSiteTerrainLine,
} from "@/lib/proposal-copy";
import {
  CUSTOM_VALUE,
  type OnboardingPhase,
} from "@/lib/onboarding-flow";
import {
  buildWizardSteps,
  dimensionPresets,
  phaseIndex,
  previousPhase,
  ROOF_PITCH_OPTIONS,
  ROOF_STYLE_OPTIONS,
  stepContent,
  stepSummary,
  USE_CASE_OPTIONS,
  type WizardStepDef,
} from "@/lib/onboarding-wizard";
import {
  SITE_BUILT_UP,
  SITE_OPEN_INDUSTRIAL,
  SITE_PIN,
} from "@/lib/site-surroundings";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";

function WizardOption({
  label,
  selected,
  disabled,
  onClick,
  icon,
}: {
  label: string;
  selected?: boolean;
  disabled?: boolean;
  onClick: () => void;
  icon?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-2xl px-4 py-3.5 text-left text-[15px] transition-all",
        "border bg-white/70 shadow-sm backdrop-blur-sm",
        selected
          ? "border-slate-300 bg-white text-slate-900 ring-1 ring-slate-200"
          : "border-slate-200/80 text-slate-700 hover:border-slate-300 hover:bg-white hover:shadow-md",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      {icon ? (
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
          {icon}
        </span>
      ) : null}
      <span className="flex-1">{label}</span>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
    </button>
  );
}

function WizardChip({
  label,
  selected,
  disabled,
  onClick,
}: {
  label: string;
  selected?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-10 items-center rounded-full px-5 text-sm font-medium transition-all",
        "border bg-white/70 shadow-sm backdrop-blur-sm",
        selected
          ? "border-slate-800 bg-slate-900 text-white shadow-md"
          : "border-slate-200/80 text-slate-600 hover:border-slate-300 hover:bg-white hover:text-slate-900",
        disabled && "opacity-50",
      )}
    >
      {label}
    </button>
  );
}

function StepIndicator({
  steps,
  currentPhase,
  onJump,
}: {
  steps: WizardStepDef[];
  currentPhase: OnboardingPhase;
  onJump: (phase: OnboardingPhase) => void;
}) {
  const currentIdx = phaseIndex(currentPhase, steps);

  return (
    <nav
      className="mb-8 flex flex-wrap items-center justify-center gap-1.5 sm:gap-2"
      aria-label="Setup progress"
    >
      {steps.map((step, idx) => {
        const done = idx < currentIdx;
        const active = step.phase === currentPhase;
        const clickable = done && !active;

        return (
          <button
            key={step.phase}
            type="button"
            disabled={!clickable}
            onClick={() => clickable && onJump(step.phase)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-all sm:px-3.5 sm:py-1.5 sm:text-[13px]",
              active && "bg-slate-900 text-white shadow-sm",
              done &&
                !active &&
                "bg-white/80 text-slate-600 shadow-sm hover:bg-white hover:text-slate-900",
              !active && !done && "text-slate-400",
              clickable && "cursor-pointer",
              !clickable && !active && "cursor-default",
            )}
          >
            {step.label}
          </button>
        );
      })}
    </nav>
  );
}

function SiteInfoCard({ locationLabel }: { locationLabel: string }) {
  const site = useProjectStore((s) => s.siteContext);
  if (!site) return null;

  const pending = isSiteClimatePending(site);

  return (
    <div className="mb-6 rounded-2xl border border-white/80 bg-white/60 p-4 text-sm leading-relaxed text-slate-600 shadow-sm backdrop-blur-sm">
      <p className="font-medium text-slate-800">{locationLabel}</p>
      {pending ? (
        <p className="mt-2 text-[13px]">
          Wind and terrain load with your proposal — pick the surroundings that
          best match your plot.
        </p>
      ) : (
        <>
          <p className="mt-2 text-[13px]">{formatClimateLine(site)}</p>
          <p className="mt-1 text-[13px]">{formatSiteTerrainLine(site)}</p>
        </>
      )}
    </div>
  );
}

function CustomMetresInput({
  placeholder,
  disabled,
  onSubmit,
}: {
  placeholder: string;
  disabled: boolean;
  onSubmit: (value: string) => void;
}) {
  const [value, setValue] = useState("");

  return (
    <form
      className="mt-4 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = value.trim();
        if (!trimmed || disabled) return;
        onSubmit(trimmed);
        setValue("");
      }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          "min-w-0 flex-1 rounded-full border border-white/80 bg-white/80 px-4 py-2.5 text-sm text-slate-800",
          "shadow-sm placeholder:text-slate-400 focus:border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-200",
        )}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className={cn(
          "shrink-0 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-sm",
          "hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400",
        )}
      >
        Continue
      </button>
    </form>
  );
}

function SiteRefineStep({
  disabled,
  onPinMode,
}: {
  disabled: boolean;
  onPinMode: () => void;
}) {
  const confirmSiteRefine = useProjectStore((s) => s.confirmSiteRefine);
  const siteContext = useProjectStore((s) => s.siteContext);
  const locationLabel = useProjectStore((s) => s.wizardStep1.location_label);
  const alreadyOpen =
    !isSiteClimatePending(siteContext) && siteContext?.exposure === "open";

  return (
    <>
      <SiteInfoCard locationLabel={locationLabel} />
      <div className="flex flex-col gap-2.5">
        <WizardOption
          label="Built-up / inside city"
          disabled={disabled}
          icon={<Building2 className="h-4 w-4" />}
          onClick={() => confirmSiteRefine(SITE_BUILT_UP)}
        />
        {!alreadyOpen ? (
          <WizardOption
            label="Open or industrial land"
            disabled={disabled}
            icon={<Factory className="h-4 w-4" />}
            onClick={() => confirmSiteRefine(SITE_OPEN_INDUSTRIAL)}
          />
        ) : null}
        <WizardOption
          label="Pin exact site on map"
          disabled={disabled}
          icon={<MapPinned className="h-4 w-4" />}
          onClick={() => {
            onPinMode();
            confirmSiteRefine(SITE_PIN);
          }}
        />
      </div>
    </>
  );
}

function ChipStep({
  options,
  selected,
  disabled,
  allowCustom,
  customPlaceholder,
  onPick,
}: {
  options: { label: string; value: string }[];
  selected?: string;
  disabled: boolean;
  allowCustom?: boolean;
  customPlaceholder?: string;
  onPick: (value: string) => void;
}) {
  const [customMode, setCustomMode] = useState(false);

  return (
    <>
      <div className="flex flex-wrap justify-center gap-2">
        {options.map((opt) => (
          <WizardChip
            key={opt.value}
            label={opt.label}
            selected={selected === opt.value}
            disabled={disabled}
            onClick={() => onPick(opt.value)}
          />
        ))}
        {allowCustom ? (
          <WizardChip
            label="Custom…"
            selected={customMode}
            disabled={disabled}
            onClick={() => setCustomMode(true)}
          />
        ) : null}
      </div>
      {customMode && allowCustom ? (
        <CustomMetresInput
          placeholder={customPlaceholder ?? "Enter value…"}
          disabled={disabled}
          onSubmit={(v) => onPick(v)}
        />
      ) : null}
    </>
  );
}

export function OnboardingWizard() {
  const phase = useProjectStore((s) => s.onboardingPhase);
  const step1 = useProjectStore((s) => s.wizardStep1);
  const step2 = useProjectStore((s) => s.wizardStep2);
  const isProposing = useProjectStore((s) => s.isProposing);
  const isLoading = useProjectStore((s) => s.isLoading);
  const statuses = useProjectStore((s) => s.statuses);
  const error = useProjectStore((s) => s.error);
  const answerOnboarding = useProjectStore((s) => s.answerOnboarding);
  const submitOnboardingCustom = useProjectStore((s) => s.submitOnboardingCustom);
  const setOnboardingPhase = useProjectStore((s) => s.setOnboardingPhase);
  const clearError = useProjectStore((s) => s.clearError);

  const [mapPinMode, setMapPinMode] = useState(false);
  const [customUseCase, setCustomUseCase] = useState(false);

  useEffect(() => {
    if (phase !== "site_refine") setMapPinMode(false);
    if (phase !== "use_case") setCustomUseCase(false);
  }, [phase]);

  const steps = useMemo(
    () => buildWizardSteps(step2, phase),
    [step2, phase],
  );
  const { title, description } = stepContent(phase, step1);
  const disabled = isProposing || isLoading;
  const isProposal = phase === "proposal";
  const wide = isProposal;

  const goBack = () => {
    if (mapPinMode) {
      setMapPinMode(false);
      return;
    }
    const prev = previousPhase(phase, steps);
    setOnboardingPhase(prev);
  };

  const pick = async (value: string) => {
    clearError();
    if (value === CUSTOM_VALUE) {
      if (phase === "use_case") setCustomUseCase(true);
      else await answerOnboarding(CUSTOM_VALUE);
      return;
    }
    await answerOnboarding(value);
  };

  const pinLat = step1.latitude ?? 0;
  const pinLon = step1.longitude ?? 0;

  return (
    <div
      className={cn(
        "flex w-full flex-col items-center px-4 sm:px-6",
        isProposal
          ? "min-h-0 justify-start py-6 sm:py-8"
          : "min-h-full justify-center py-8 sm:py-10",
      )}
    >
      <div
        className={cn(
          "flex w-full flex-col items-center",
          wide ? "max-w-2xl" : "max-w-[640px]",
        )}
      >
        {!isProposal ? (
          <SteeleraMark
            size="md"
            className="animate-onboarding-fade-up mb-6 sm:mb-8"
          />
        ) : (
          <SteeleraMark size="sm" className="mb-4 sm:mb-5" />
        )}

        {!isProposal ? (
          <StepIndicator
            steps={steps}
            currentPhase={phase}
            onJump={setOnboardingPhase}
          />
        ) : null}

        <div className="animate-onboarding-fade-up onboarding-delay-1 w-full text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            {mapPinMode ? "Pin your site" : title}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500 sm:text-[15px]">
            {mapPinMode
              ? "Click the map to place the pin on your exact plot."
              : description}
          </p>
        </div>

        <div className="animate-onboarding-fade-up onboarding-delay-2 mt-8 w-full">
          {phase === "site_refine" && !mapPinMode ? (
            <SiteRefineStep
              disabled={disabled}
              onPinMode={() => setMapPinMode(true)}
            />
          ) : null}

          {phase === "site_refine" && mapPinMode && step1.latitude !== null ? (
            <div className="mx-auto max-w-md">
              <SiteMapPinPicker
                initialLat={pinLat}
                initialLon={pinLon}
                active
                onComplete={() => setMapPinMode(false)}
              />
            </div>
          ) : null}

          {phase === "use_case" && !customUseCase ? (
            <div className="flex flex-wrap justify-center gap-2">
              {USE_CASE_OPTIONS.map((opt) => (
                <WizardChip
                  key={opt.value}
                  label={opt.label}
                  selected={step1.use_case === opt.value}
                  disabled={disabled}
                  onClick={() => pick(opt.value)}
                />
              ))}
              <WizardChip
                label="Other…"
                disabled={disabled}
                onClick={() => setCustomUseCase(true)}
              />
            </div>
          ) : null}

          {phase === "use_case" && customUseCase ? (
            <CustomMetresInput
              placeholder="Describe your structure…"
              disabled={disabled}
              onSubmit={(v) => submitOnboardingCustom(v)}
            />
          ) : null}

          {phase === "width" ? (
            <ChipStep
              options={dimensionPresets("width")}
              selected={String(step1.width_mm)}
              disabled={disabled}
              allowCustom
              customPlaceholder="e.g. 16"
              onPick={pick}
            />
          ) : null}

          {phase === "length" ? (
            <ChipStep
              options={dimensionPresets("length")}
              selected={String(step1.length_mm)}
              disabled={disabled}
              allowCustom
              customPlaceholder="e.g. 35"
              onPick={pick}
            />
          ) : null}

          {phase === "height" ? (
            <ChipStep
              options={dimensionPresets("height")}
              selected={String(step1.height_mm)}
              disabled={disabled}
              allowCustom
              customPlaceholder="e.g. 6.5"
              onPick={pick}
            />
          ) : null}

          {phase === "roof_style" ? (
            <div className="flex flex-wrap justify-center gap-2">
              {ROOF_STYLE_OPTIONS.map((opt) => (
                <WizardChip
                  key={opt.value}
                  label={opt.label}
                  selected={step2.roof_style === opt.value}
                  disabled={disabled}
                  onClick={() => pick(opt.value)}
                />
              ))}
            </div>
          ) : null}

          {phase === "roof_pitch" ? (
            <div className="flex flex-wrap justify-center gap-2">
              {ROOF_PITCH_OPTIONS.map((deg) => (
                <WizardChip
                  key={deg}
                  label={`${deg}°`}
                  selected={String(step2.roof_pitch_deg) === deg}
                  disabled={disabled}
                  onClick={() => pick(deg)}
                />
              ))}
            </div>
          ) : null}

          {phase === "proposal" ? (
            <div className="mt-2">
              {isProposing ? (
                <div className="py-12">
                  <OnboardingLoader
                    label="Building your model"
                    sublabel={statuses[0] ?? "Generating preliminary structure…"}
                  />
                </div>
              ) : (
                <ChatProposalBlock active variant="wizard" />
              )}
            </div>
          ) : null}

          {statuses.length > 0 && phase !== "proposal" ? (
            <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin text-slate-700" />
              {statuses[0]}
            </div>
          ) : null}

          {error ? (
            <p className="mt-4 text-center text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        {!isProposal ? (
          <div className="mt-10 flex w-full items-center justify-between">
            <button
              type="button"
              onClick={goBack}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm text-slate-500 transition-colors hover:bg-white/60 hover:text-slate-800"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            {stepSummary(phase, step1, step2) ? (
              <p className="text-xs text-slate-400">
                Selected:{" "}
                <span className="font-medium text-slate-600">
                  {stepSummary(phase, step1, step2)}
                </span>
              </p>
            ) : (
              <span />
            )}
          </div>
        ) : (
          <div className="mt-8 flex w-full justify-start">
            <button
              type="button"
              onClick={goBack}
              disabled={isProposing}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm text-slate-500 transition-colors hover:bg-white/60 hover:text-slate-800 disabled:opacity-40"
            >
              <ArrowLeft className="h-4 w-4" />
              Edit setup
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

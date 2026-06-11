"use client";

import {
  ArrowLeft,
  ArrowUp,
  Building2,
  Layers,
  Loader2,
  MapPin,
  Paperclip,
  TrendingUp,
  Warehouse,
} from "lucide-react";
import { useCallback, useState } from "react";

import { OnboardingLoader } from "@/components/onboarding/OnboardingLoader";
import { SteeleraMark } from "@/components/onboarding/SteeleraMark";
import { ClientOnly } from "@/components/ui/client-only";
import { onboardingTheme } from "@/lib/onboarding-theme";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";

type StartStep = "structure" | "location";

type StructureChip = {
  label: string;
  useCase: string;
  icon: typeof Warehouse;
};

const STRUCTURE_CHIPS: StructureChip[] = [
  { label: "Portal shed", useCase: "Portal shed", icon: Warehouse },
  { label: "Mezzanine", useCase: "Mezzanine", icon: Layers },
  { label: "Stairs", useCase: "Stairs", icon: TrendingUp },
  { label: "Pipe rack", useCase: "Pipe rack", icon: Building2 },
];

export function OnboardingStartScreen() {
  const [startStep, setStartStep] = useState<StartStep>("structure");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedUseCase, setSelectedUseCase] = useState<string | null>(null);

  const submitOnboardingCustom = useProjectStore((s) => s.submitOnboardingCustom);
  const setOnboardingLocation = useProjectStore((s) => s.setOnboardingLocation);
  const updateWizardStep1 = useProjectStore((s) => s.updateWizardStep1);
  const isProposing = useProjectStore((s) => s.isProposing);
  const error = useProjectStore((s) => s.error);
  const clearError = useProjectStore((s) => s.clearError);

  const disabled = loading || isProposing;
  const isLocationStep = startStep === "location";

  const goToLocationStep = useCallback(
    (useCase: string) => {
      setSelectedUseCase(useCase);
      updateWizardStep1({ use_case: useCase });
      setInput("");
      clearError();
      setStartStep("location");
    },
    [clearError, updateWizardStep1],
  );

  const pickUseCase = useCallback(
    (useCase: string) => {
      if (disabled) return;
      goToLocationStep(useCase);
    },
    [disabled, goToLocationStep],
  );

  const handleStructureSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value || disabled) return;
    goToLocationStep(value);
  };

  const handleLocationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value || disabled) return;
    setLoading(true);
    clearError();
    try {
      await submitOnboardingCustom(value);
      setInput("");
    } finally {
      setLoading(false);
    }
  };

  const useGeolocation = () => {
    if (disabled || !navigator.geolocation) return;
    setLoading(true);
    clearError();
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          await setOnboardingLocation(
            pos.coords.latitude,
            pos.coords.longitude,
            "My current location",
          );
        } finally {
          setLoading(false);
        }
      },
      () => setLoading(false),
      { enableHighAccuracy: false, timeout: 12_000, maximumAge: 60_000 },
    );
  };

  const goBackToStructure = () => {
    if (disabled) return;
    clearError();
    setInput("");
    setStartStep("structure");
  };

  const structurePlaceholder =
    "Describe a portal shed, mezzanine, stairs, pipe rack…";
  const locationPlaceholder = selectedUseCase
    ? `Where is your ${selectedUseCase.toLowerCase()}? City or address…`
    : "City, address, or postcode…";

  return (
    <ClientOnly fallback={<OnboardingStartFallback />}>
      <div className="flex min-h-full w-full flex-col items-center justify-center px-4 py-10 sm:px-6">
        <div className="flex w-full max-w-[900px] flex-col items-center">
          <SteeleraMark
            size="md"
            className="animate-onboarding-fade-up mb-8 sm:mb-10"
          />

          {isLocationStep ? (
            <>
              <button
                type="button"
                onClick={goBackToStructure}
                disabled={disabled}
                className="animate-onboarding-fade-up mb-6 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm text-slate-500 transition-colors hover:bg-white/60 hover:text-slate-800 disabled:opacity-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Change structure
              </button>

              <h1 className="animate-onboarding-fade-up onboarding-delay-1 max-w-2xl text-center text-[1.75rem] font-semibold leading-[1.15] tracking-tight text-slate-900 sm:text-4xl">
                Where is your project?
              </h1>

              <p className="animate-onboarding-fade-up onboarding-delay-2 mt-3 max-w-lg text-center text-sm leading-relaxed text-slate-500 sm:text-[15px]">
                {selectedUseCase ? (
                  <>
                    Building a{" "}
                    <span className="font-medium text-slate-700">
                      {selectedUseCase.toLowerCase()}
                    </span>
                    . Enter the site location so we can load wind and terrain
                    data.
                  </>
                ) : (
                  "Enter the site location so we can load wind and terrain data."
                )}
              </p>
            </>
          ) : (
            <>
              <h1 className="animate-onboarding-fade-up onboarding-delay-1 max-w-2xl text-center text-[1.75rem] font-semibold leading-[1.15] tracking-tight text-slate-900 sm:text-4xl">
                What structure are we building today?
              </h1>

              <p className="animate-onboarding-fade-up onboarding-delay-2 mt-3 max-w-lg text-center text-sm leading-relaxed text-slate-500 sm:text-[15px]">
                Pick a type or describe your project — Steelera will create a
                preliminary structural model for you.
              </p>
            </>
          )}

          <form
            onSubmit={isLocationStep ? handleLocationSubmit : handleStructureSubmit}
            suppressHydrationWarning
            className="animate-onboarding-fade-up onboarding-delay-3 mt-8 w-full min-w-0 sm:mt-10"
          >
            <div
              suppressHydrationWarning
              className={cn(
                "mx-auto flex h-[60px] w-full min-w-0 max-w-[860px] items-center gap-2 rounded-2xl sm:h-[68px]",
                "border bg-white/80 shadow-[0_8px_40px_rgba(15,23,42,0.06)]",
                "backdrop-blur-xl transition-all duration-300",
                "focus-within:border-slate-300 focus-within:shadow-[0_12px_48px_rgba(15,23,42,0.1)]",
                "px-3 sm:px-4",
              )}
              style={{ borderColor: onboardingTheme.glassBorder }}
            >
              {!isLocationStep ? (
                <button
                  type="button"
                  disabled={disabled}
                  suppressHydrationWarning
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100/80 hover:text-slate-600 disabled:opacity-40"
                  aria-label="Attach file"
                >
                  <Paperclip className="h-5 w-5" />
                </button>
              ) : (
                <span className="flex h-10 w-10 shrink-0 items-center justify-center text-slate-400">
                  <MapPin className="h-5 w-5" />
                </span>
              )}

              <input
                value={input}
                onChange={(e) => {
                  if (error) clearError();
                  setInput(e.target.value);
                }}
                placeholder={
                  isLocationStep ? locationPlaceholder : structurePlaceholder
                }
                disabled={disabled}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore
                data-form-type="other"
                suppressHydrationWarning
                className="min-w-0 flex-1 bg-transparent text-base text-slate-800 placeholder:text-slate-400 focus:outline-none sm:text-[17px]"
              />

              <button
                type="submit"
                disabled={disabled || !input.trim()}
                suppressHydrationWarning
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl sm:h-11 sm:w-11",
                  "bg-slate-900 text-white shadow-sm transition-all duration-200",
                  "hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none",
                )}
                aria-label={isLocationStep ? "Confirm location" : "Continue"}
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <ArrowUp className="h-5 w-5" />
                )}
              </button>
            </div>
          </form>

          {error ? (
            <p
              className="animate-onboarding-fade-up mt-3 text-center text-sm text-red-600"
              role="alert"
            >
              {error}
            </p>
          ) : null}

          {isProposing ? (
            <div className="mt-8">
              <OnboardingLoader
                label="Analyzing your request"
                sublabel="Preparing structural setup…"
              />
            </div>
          ) : isLocationStep ? (
            <div className="animate-onboarding-fade-up onboarding-delay-4 mt-6 flex flex-wrap items-center justify-center gap-2 sm:mt-8">
              <button
                type="button"
                disabled={disabled}
                suppressHydrationWarning
                onClick={useGeolocation}
                className={cn(
                  "inline-flex h-9 items-center gap-2 rounded-full px-4 text-sm",
                  "border border-slate-200/80 bg-white/60 text-slate-600 shadow-sm backdrop-blur-sm",
                  "transition-all hover:border-slate-300 hover:bg-white hover:text-slate-900",
                  disabled && "opacity-50",
                )}
              >
                <MapPin className="h-4 w-4 shrink-0 text-slate-500" />
                Use my location
              </button>
            </div>
          ) : (
            <div className="animate-onboarding-fade-up onboarding-delay-4 mt-6 flex w-full flex-wrap items-center justify-center gap-2 sm:mt-8">
              {STRUCTURE_CHIPS.map((chip) => {
                const Icon = chip.icon;
                const active = selectedUseCase === chip.useCase;
                return (
                  <button
                    key={chip.label}
                    type="button"
                    disabled={disabled}
                    suppressHydrationWarning
                    onClick={() => pickUseCase(chip.useCase)}
                    className={cn(
                      "inline-flex h-9 items-center gap-2 rounded-full px-4 text-sm transition-all duration-200",
                      "border bg-white/75 shadow-sm backdrop-blur-sm",
                      active
                        ? "border-slate-300 bg-white text-slate-900 ring-1 ring-slate-200"
                        : "border-slate-200/80 text-slate-600 hover:border-slate-300 hover:bg-white hover:text-slate-900",
                      disabled && "opacity-50",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0 text-slate-500" />
                    {chip.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </ClientOnly>
  );
}

function OnboardingStartFallback() {
  return (
    <div className="flex min-h-full w-full flex-col items-center justify-center px-4 py-10 sm:px-6">
      <div className="flex w-full max-w-[900px] flex-col items-center">
        <SteeleraMark size="md" className="mb-8 sm:mb-10" />
        <h1 className="max-w-2xl text-center text-[1.75rem] font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl">
          What structure are we building today?
        </h1>
        <p className="mt-3 max-w-lg text-center text-sm leading-relaxed text-slate-500 sm:text-[15px]">
          Pick a type or describe your project — Steelera will create a
          preliminary structural model for you.
        </p>
      </div>
    </div>
  );
}

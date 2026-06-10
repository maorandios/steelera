"use client";

import {
  ArrowUp,
  Building2,
  Layers,
  Loader2,
  MapPin,
  Paperclip,
  TrendingUp,
  Upload,
  Warehouse,
} from "lucide-react";
import { useCallback, useState } from "react";

import { SteeleraMark } from "@/components/onboarding/SteeleraMark";
import { ClientOnly } from "@/components/ui/client-only";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";

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

  const pickUseCase = useCallback(
    (useCase: string) => {
      if (disabled) return;
      clearError();
      setSelectedUseCase(useCase);
      updateWizardStep1({ use_case: useCase });
    },
    [clearError, disabled, updateWizardStep1],
  );

  const handleSubmit = async (e: React.FormEvent) => {
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

  const placeholder = selectedUseCase
    ? `Where is your ${selectedUseCase.toLowerCase()}? City or address…`
    : "Describe a portal shed, mezzanine, stairs, pipe rack…";

  return (
    <ClientOnly fallback={<OnboardingStartFallback />}>
      <div className="relative z-10 flex min-h-dvh w-full flex-col items-center justify-center px-4 py-10 sm:px-6">
      <div className="flex w-full max-w-[900px] flex-col items-center">
        <SteeleraMark size="md" className="mb-8 sm:mb-10" />

        <h1 className="max-w-2xl text-center text-[1.75rem] font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl sm:leading-tight">
          What structure are we building today?
        </h1>

        <p className="mt-3 max-w-lg text-center text-sm leading-relaxed text-slate-500 sm:text-[15px]">
          Describe your project and Steelera will create a preliminary structural
          model for you.
        </p>

        <form
          onSubmit={handleSubmit}
          suppressHydrationWarning
          className="mt-8 w-full min-w-0 sm:mt-10"
        >
          <div
            suppressHydrationWarning
            className={cn(
              "mx-auto flex h-[60px] w-full min-w-0 max-w-[860px] items-center gap-2 rounded-full sm:h-[72px]",
              "border border-white/70 bg-white/75 shadow-[0_8px_40px_rgba(15,23,42,0.08)]",
              "backdrop-blur-xl transition-shadow focus-within:shadow-[0_12px_48px_rgba(37,99,235,0.12)]",
              "px-3 sm:px-4",
            )}
          >
            <button
              type="button"
              disabled={disabled}
              suppressHydrationWarning
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
              aria-label="Attach file"
            >
              <Paperclip className="h-5 w-5" />
            </button>

            <input
              value={input}
              onChange={(e) => {
                if (error) clearError();
                setInput(e.target.value);
              }}
              placeholder={placeholder}
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
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-full sm:h-11 sm:w-11",
                "bg-blue-600 text-white shadow-md transition-all",
                "hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none",
              )}
              aria-label="Send"
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
          <p className="mt-3 text-center text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex w-full flex-wrap items-center justify-center gap-2 sm:mt-8">
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
                  "inline-flex h-9 items-center gap-2 rounded-full px-4 text-sm transition-all",
                  "border bg-white/70 shadow-sm backdrop-blur-sm",
                  active
                    ? "border-blue-200 bg-blue-50/90 text-blue-900"
                    : "border-white/80 text-slate-600 hover:border-slate-200 hover:bg-white hover:text-slate-900",
                  disabled && "opacity-50",
                )}
              >
                <Icon className="h-4 w-4 shrink-0 text-blue-600" />
                {chip.label}
              </button>
            );
          })}
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            disabled={disabled}
            suppressHydrationWarning
            onClick={useGeolocation}
            className={cn(
              "inline-flex h-9 items-center gap-2 rounded-full px-4 text-sm",
              "border border-white/80 bg-white/60 text-slate-600 shadow-sm backdrop-blur-sm",
              "transition-all hover:border-slate-200 hover:bg-white hover:text-slate-900",
              disabled && "opacity-50",
            )}
          >
            <MapPin className="h-4 w-4 shrink-0 text-blue-600" />
            Use my location
          </button>
          <button
            type="button"
            disabled={disabled}
            suppressHydrationWarning
            onClick={() => {
              clearError();
              useProjectStore.setState({
                error:
                  "IFC upload opens from the workspace after your first model is built.",
              });
            }}
            className={cn(
              "inline-flex h-9 items-center gap-2 rounded-full px-4 text-sm",
              "border border-white/80 bg-white/60 text-slate-600 shadow-sm backdrop-blur-sm",
              "transition-all hover:border-slate-200 hover:bg-white hover:text-slate-900",
              disabled && "opacity-50",
            )}
          >
            <Upload className="h-4 w-4 shrink-0 text-blue-600" />
            Upload IFC
          </button>
        </div>
      </div>
      </div>
    </ClientOnly>
  );
}

function OnboardingStartFallback() {
  return (
    <div className="relative z-10 flex min-h-dvh w-full flex-col items-center justify-center px-4 py-10 sm:px-6">
      <div className="flex w-full max-w-[900px] flex-col items-center">
        <SteeleraMark size="md" className="mb-8 sm:mb-10" />
        <h1 className="max-w-2xl text-center text-[1.75rem] font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl sm:leading-tight">
          What structure are we building today?
        </h1>
        <p className="mt-3 max-w-lg text-center text-sm leading-relaxed text-slate-500 sm:text-[15px]">
          Describe your project and Steelera will create a preliminary structural
          model for you.
        </p>
      </div>
    </div>
  );
}

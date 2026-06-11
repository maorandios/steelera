import { onboardingTheme } from "@/lib/onboarding-theme";
import { cn } from "@/lib/utils";

type SteeleraMarkProps = {
  className?: string;
  size?: "sm" | "md";
  animate?: boolean;
};

export function SteeleraMark({
  className,
  size = "md",
  animate = true,
}: SteeleraMarkProps) {
  const icon = size === "sm" ? 22 : 28;
  const text = size === "sm" ? "text-sm" : "text-base";

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-2.5",
        animate && "animate-onboarding-breathe",
        className,
      )}
    >
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden
        className="shrink-0"
      >
        <path
          d="M16 4L28 11V21L16 28L4 21V11L16 4Z"
          stroke={onboardingTheme.accent}
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
        <path
          d="M16 4V28M4 11L16 18L28 11M4 21L16 14L28 21"
          stroke={onboardingTheme.accentSoft}
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
      </svg>
      <span
        className={cn(
          "font-semibold tracking-[0.22em] text-slate-800",
          text,
        )}
      >
        STEELERA
      </span>
    </div>
  );
}

import { cn } from "@/lib/utils";

type SteeleraMarkProps = {
  className?: string;
  size?: "sm" | "md";
};

export function SteeleraMark({ className, size = "md" }: SteeleraMarkProps) {
  const icon = size === "sm" ? 22 : 28;
  const text = size === "sm" ? "text-sm" : "text-base";

  return (
    <div className={cn("flex items-center justify-center gap-2.5", className)}>
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
          stroke="#2563eb"
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
        <path
          d="M16 4V28M4 11L16 18L28 11M4 21L16 14L28 21"
          stroke="#2563eb"
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
      </svg>
      <span
        className={cn(
          "font-semibold tracking-[0.18em] text-slate-800",
          text,
        )}
      >
        STEELERA
      </span>
    </div>
  );
}

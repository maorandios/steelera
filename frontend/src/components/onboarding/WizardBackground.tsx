"use client";

export function WizardBackground({ sharp = false }: { sharp?: boolean }) {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden transition-[filter,opacity] duration-700 ease-out"
      style={{ filter: sharp ? "none" : "blur(28px)", opacity: sharp ? 1 : 0.85 }}
      aria-hidden
    >
      <div
        className="absolute inset-0 animate-gradient-shift"
        style={{
          background:
            "linear-gradient(135deg, #e8eef5 0%, #dce6f0 25%, #cfd9e8 50%, #e2e8f0 75%, #d4dce8 100%)",
          backgroundSize: "400% 400%",
        }}
      />
      <div
        className="absolute left-1/2 top-1/2 h-[min(70vw,520px)] w-[min(90vw,900px)] -translate-x-1/2 -translate-y-1/2 opacity-[0.12]"
        style={{
          background:
            "repeating-linear-gradient(90deg, transparent, transparent 48px, #64748b 48px, #64748b 49px), repeating-linear-gradient(0deg, transparent, transparent 32px, #64748b 32px, #64748b 33px)",
          transform: "translate(-50%, -50%) perspective(800px) rotateX(58deg) rotateZ(-8deg)",
        }}
      />
    </div>
  );
}

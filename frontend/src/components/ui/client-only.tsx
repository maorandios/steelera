"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * Renders children only after mount. Avoids hydration mismatches when browser
 * extensions inject attributes (e.g. fdprocessedid) into form controls.
 */
export function ClientOnly({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return fallback;
  }

  return children;
}

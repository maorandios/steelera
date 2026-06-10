/** User-facing message for failed fetch / abort (browser extensions, timeouts, navigation). */

export function isFetchAborted(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  if (err.name === "AbortError" || err.name === "TimeoutError") return true;
  return /abort/i.test(err.message);
}

export function formatApiError(
  err: unknown,
  options: {
    timeout?: string;
    network?: string;
    fallback?: string;
  } = {},
): string {
  const {
    timeout = "Request timed out. Please try again.",
    network =
      "Cannot reach Steelera backend. Start it with: cd backend && python -m uvicorn main:app --reload --port 8000",
    fallback = "Something went wrong. Please try again.",
  } = options;

  if (isFetchAborted(err)) return timeout;
  if (err instanceof TypeError) return network;
  if (err instanceof Error && err.message.trim()) return err.message;
  return fallback;
}

export function abortAfterMs(ms: number): {
  signal: AbortSignal;
  clear: () => void;
} {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort(
      new DOMException("Request timed out", "TimeoutError"),
    );
  }, ms);
  return {
    signal: controller.signal,
    clear: () => clearTimeout(timeoutId),
  };
}

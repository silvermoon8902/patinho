/**
 * Haptic feedback helpers. No-op when the browser doesn't expose the
 * Vibration API or when the user has opted out via their profile.
 */

const STORAGE_KEY = "patinho-haptic-enabled";

export function hapticEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if (!("vibrate" in navigator)) return false;
  const stored = localStorage.getItem(STORAGE_KEY);
  // Default: enabled. Only disabled when the user explicitly opts out.
  return stored !== "false";
}

export function setHapticEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

function safeVibrate(pattern: number | number[]): void {
  if (!hapticEnabled()) return;
  try {
    navigator.vibrate(pattern);
  } catch {
    /* swallow */
  }
}

/** Short tap — use for button presses, tab switches. */
export function hapticTap(): void {
  safeVibrate(10);
}

/** Heavier — use for confirming or completing a critical action. */
export function hapticSuccess(): void {
  safeVibrate([30, 50, 30]);
}

/** Double buzz — use for errors/denials. */
export function hapticError(): void {
  safeVibrate([50, 80, 50]);
}

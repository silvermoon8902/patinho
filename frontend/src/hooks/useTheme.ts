import { useCallback, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "patinho-theme";

function readTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === "light" || stored === "dark") return stored;
  // Default to light explicitly — dark mode currently has contrast gaps
  // on a few screens (Bolão CTA on bet creation, etc.) that we'll polish
  // before respecting prefers-color-scheme again. Users can still flip
  // to dark via the toggle in the header.
  return "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(STORAGE_KEY, theme);
}

// Initialize on module load so the document attribute is set before first render
if (typeof window !== "undefined") {
  applyTheme(readTheme());
}

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notify() {
  listeners.forEach((l) => l());
}

function getSnapshot(): Theme {
  return readTheme();
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, () => "light" as Theme);

  const setTheme = useCallback((next: Theme) => {
    applyTheme(next);
    notify();
  }, []);

  const toggleTheme = useCallback(() => {
    const next: Theme = readTheme() === "light" ? "dark" : "light";
    applyTheme(next);
    notify();
  }, []);

  return { theme, setTheme, toggleTheme };
}

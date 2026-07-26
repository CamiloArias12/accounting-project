/**
 * Browser-side persistence of user preferences.
 *
 * These live at module scope on purpose: mutating `document` from inside a
 * component body trips React's immutability lint, and keeping the side effects
 * in one place makes them easy to find.
 */
import type { Theme } from "@/lib/theme";

const ONE_YEAR = 60 * 60 * 24 * 365;

export function persistPreference(name: string, value: string): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${ONE_YEAR}; samesite=lax`;
}

/** Writes the resolved theme to `<html>`, which is what the CSS reads. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = resolveTheme(theme);
}

export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export const THEMES = ["light", "dark", "system"] as const;
export type Theme = (typeof THEMES)[number];

export const DEFAULT_THEME: Theme = "system";

// Cookie the theme choice is stored in, so the server can render it.
export const THEME_COOKIE = "theme";

export type ResolvedTheme = "light" | "dark";

export function isTheme(value: string | undefined): value is Theme {
  return value !== undefined && THEMES.includes(value as Theme);
}

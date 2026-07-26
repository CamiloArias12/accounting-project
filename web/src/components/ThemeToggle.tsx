"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { applyTheme, persistPreference } from "@/lib/preferences";
import { THEMES, THEME_COOKIE, type Theme } from "@/lib/theme";

interface Props {
  /** Choice stored in the cookie, so the first render matches the server. */
  initialTheme: Theme;
}

const ICONS: Record<Theme, string> = {
  light: "☀",
  dark: "☾",
  system: "◐",
};

export function ThemeToggle({ initialTheme }: Props) {
  const t = useTranslations("theme");
  const [theme, setTheme] = useState<Theme>(initialTheme);

  function choose(next: Theme) {
    setTheme(next);
    persistPreference(THEME_COOKIE, next);
    // Applied straight to the DOM rather than through a server round trip: a
    // theme switch should be instant, and the cookie only needs to be right by
    // the next server render.
    applyTheme(next);
  }

  return (
    <div
      role="group"
      aria-label={t("label")}
      className="flex rounded-md border border-border p-0.5"
    >
      {THEMES.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => choose(option)}
          aria-pressed={theme === option}
          title={t(option)}
          className={`flex-1 rounded px-2 py-1 text-xs transition-colors ${
            theme === option
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-foreground/5"
          }`}
        >
          <span aria-hidden>{ICONS[option]}</span>
          <span className="sr-only">{t(option)}</span>
        </button>
      ))}
    </div>
  );
}

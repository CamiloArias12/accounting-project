"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { applyTheme, persistPreference } from "@/lib/preferences";
import { cn } from "@/lib/utils";
import { THEMES, THEME_COOKIE, type Theme } from "@/lib/theme";

interface Props {
  /** Choice stored in the cookie, so the first render matches the server. */
  initialTheme: Theme;
}

const ICONS: Record<Theme, LucideIcon> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
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
      className="flex flex-1 gap-0.5 rounded-lg bg-muted p-0.5 ring-1 ring-border/60"
    >
      {THEMES.map((option) => {
        const Icon = ICONS[option];
        const active = theme === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => choose(option)}
            aria-pressed={active}
            title={t(option)}
            className={cn(
              "grid flex-1 place-items-center rounded-md py-1.5 transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
              active
                ? "bg-card text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" />
            <span className="sr-only">{t(option)}</span>
          </button>
        );
      })}
    </div>
  );
}

"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { LOCALES, LOCALE_COOKIE, type Locale } from "@/i18n/config";
import { persistPreference } from "@/lib/preferences";
import { cn } from "@/lib/utils";

export function LocaleToggle() {
  const t = useTranslations("locale");
  const current = useLocale() as Locale;
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function choose(next: Locale) {
    persistPreference(LOCALE_COOKIE, next);
    // Unlike the theme, messages are resolved on the server, so the page has to
    startTransition(() => router.refresh());
  }

  return (
    <div
      role="group"
      aria-label={t("label")}
      className={cn(
        "flex gap-0.5 rounded-lg bg-muted p-0.5 ring-1 ring-border/60 transition-opacity",
        pending && "opacity-60",
      )}
    >
      {LOCALES.map((locale) => (
        <button
          key={locale}
          type="button"
          onClick={() => choose(locale)}
          aria-pressed={current === locale}
          className={cn(
            "rounded-md px-2.5 py-1.5 text-xs font-medium uppercase tracking-wide transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
            current === locale
              ? "bg-card text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {locale}
        </button>
      ))}
    </div>
  );
}

"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { LOCALES, LOCALE_COOKIE, type Locale } from "@/i18n/config";
import { persistPreference } from "@/lib/preferences";

export function LocaleToggle() {
  const t = useTranslations("locale");
  const current = useLocale() as Locale;
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function choose(next: Locale) {
    persistPreference(LOCALE_COOKIE, next);
    // Unlike the theme, messages are resolved on the server, so the page has to
    // be re-rendered for the new language to take effect.
    startTransition(() => router.refresh());
  }

  return (
    <div
      role="group"
      aria-label={t("label")}
      className={`flex rounded-md border border-border p-0.5 ${
        pending ? "opacity-60" : ""
      }`}
    >
      {LOCALES.map((locale) => (
        <button
          key={locale}
          type="button"
          onClick={() => choose(locale)}
          aria-pressed={current === locale}
          className={`flex-1 rounded px-2 py-1 text-xs uppercase transition-colors ${
            current === locale
              ? "bg-accent text-accent-foreground"
              : "text-muted hover:bg-foreground/5"
          }`}
        >
          {locale}
        </button>
      ))}
    </div>
  );
}

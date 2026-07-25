"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { LocaleToggle } from "@/components/LocaleToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Theme } from "@/lib/theme";

interface NavItem {
  href: string;
  labelKey: "overview" | "accounts";
  icon: string;
}

const NAV: NavItem[] = [
  { href: "/", labelKey: "overview", icon: "▤" },
  { href: "/accounts", labelKey: "accounts", icon: "▦" },
];

interface Props {
  initialTheme: Theme;
}

export function Sidebar({ initialTheme }: Props) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  // Collapsed by default on small screens; the toggle is hidden from lg up,
  // where the sidebar is always visible.
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="sidebar"
        className="fixed left-3 top-3 z-30 rounded-md border border-border bg-surface px-3 py-1.5 text-sm lg:hidden"
      >
        <span aria-hidden>☰</span>
        <span className="sr-only">{t("menu")}</span>
      </button>

      {open && (
        <button
          type="button"
          aria-label={t("close")}
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
        />
      )}

      <aside
        id="sidebar"
        className={`fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-border bg-surface transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-border px-4 py-4">
          <p className="text-sm font-semibold tracking-tight">{t("brand")}</p>
          <p className="text-xs text-muted">{t("tagline")}</p>
        </div>

        <nav className="flex-1 overflow-y-auto p-2">
          <ul className="flex flex-col gap-0.5">
            {NAV.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                      active
                        ? "bg-accent/10 font-medium text-accent"
                        : "text-foreground/80 hover:bg-foreground/5"
                    }`}
                  >
                    <span aria-hidden className="text-xs opacity-70">
                      {item.icon}
                    </span>
                    {t(item.labelKey)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="flex flex-col gap-2 border-t border-border p-3">
          <ThemeToggle initialTheme={initialTheme} />
          <LocaleToggle />
        </div>
      </aside>
    </>
  );
}

/** `/` only matches itself; deeper routes match by prefix. */
function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

"use client";

import {
  BookOpen,
  CalendarRange,
  FileCode2,
  LayoutDashboard,
  ListTree,
  Menu,
  ReceiptText,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { LocaleToggle } from "@/components/LocaleToggle";
import { SessionPanel } from "@/components/SessionPanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/utils";
import type { Theme } from "@/lib/theme";

type NavLabel =
  | "overview"
  | "accounts"
  | "thirdParties"
  | "vouchers"
  | "ledger"
  | "periods"
  | "exogena";

interface NavItem {
  href: string;
  labelKey: NavLabel;
  icon: LucideIcon;
}

interface NavGroup {
  titleKey: "groupGeneral" | "groupRecords" | "groupAccounting";
  items: NavItem[];
}

/**
 * Grouped rather than a flat list of six.
 *
 * The distinction is real and worth showing: two of these screens are master
 * data that is edited once and read forever, three are the books themselves.
 */
const NAV: NavGroup[] = [
  {
    titleKey: "groupGeneral",
    items: [{ href: "/", labelKey: "overview", icon: LayoutDashboard }],
  },
  {
    titleKey: "groupRecords",
    items: [
      { href: "/accounts", labelKey: "accounts", icon: ListTree },
      { href: "/third-parties", labelKey: "thirdParties", icon: Users },
    ],
  },
  {
    titleKey: "groupAccounting",
    items: [
      { href: "/vouchers", labelKey: "vouchers", icon: ReceiptText },
      { href: "/ledger", labelKey: "ledger", icon: BookOpen },
      { href: "/periods", labelKey: "periods", icon: CalendarRange },
      { href: "/exogena", labelKey: "exogena", icon: FileCode2 },
    ],
  },
];

interface Props {
  initialTheme: Theme;
  /** Null when nobody is signed in. */
  userEmail: string | null;
}

export function Sidebar({ initialTheme, userEmail }: Props) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  // Collapsed by default on small screens; the toggle is hidden from lg up,
  // where the sidebar is always visible.
  const [open, setOpen] = useState(false);

  // Escape closes the drawer. On a phone the overlay is the only other way
  // out, and it is easy to miss that it is tappable.
  useEffect(() => {
    if (!open) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="sidebar"
        className="fixed left-3 top-3 z-50 grid size-9 place-items-center rounded-lg bg-card/90 text-foreground shadow-sm ring-1 ring-border backdrop-blur transition-colors hover:bg-card lg:hidden"
      >
        {open ? (
          <X className="size-4" />
        ) : (
          <Menu className="size-4" />
        )}
        <span className="sr-only">{open ? t("close") : t("menu")}</span>
      </button>

      {open && (
        <button
          type="button"
          aria-label={t("close")}
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-foreground/25 backdrop-blur-[2px] lg:hidden"
        />
      )}

      <aside
        id="sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-200 ease-out lg:translate-x-0",
          open ? "translate-x-0 shadow-xl" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          {/* A mark rather than a wordmark alone: it gives the shell a fixed
              point that survives the brand name being long in either language. */}
          <span
            aria-hidden
            className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary to-indigo-500 text-sm font-bold text-primary-foreground shadow-sm"
          >
            AP
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight">
              {t("brand")}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {t("tagline")}
            </p>
          </div>
        </div>

        <nav className="scrollbar-slim flex-1 overflow-y-auto px-3 pb-2">
          {NAV.map((group) => (
            <div key={group.titleKey} className="mb-4 last:mb-0">
              <p className="px-3 pb-1.5 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-muted-foreground/80">
                {t(group.titleKey)}
              </p>
              <ul className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const active = isActive(pathname, item.href);
                  const Icon = item.icon;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                          active
                            ? "bg-primary/10 font-medium text-primary"
                            : "text-foreground/75 hover:bg-sidebar-accent hover:text-foreground",
                        )}
                      >
                        {/* The rail, not a border: it marks the active row
                            without shifting the label by a pixel. */}
                        {active && (
                          <span
                            aria-hidden
                            className="absolute inset-y-1.5 -left-3 w-1 rounded-r-full bg-primary"
                          />
                        )}
                        <Icon
                          className={cn(
                            "size-4 shrink-0 transition-colors",
                            active
                              ? "text-primary"
                              : "text-muted-foreground group-hover:text-foreground",
                          )}
                        />
                        <span className="truncate">{t(item.labelKey)}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="flex flex-col gap-3 border-t border-sidebar-border p-3">
          <SessionPanel email={userEmail} />
          <div className="flex items-center gap-2">
            <ThemeToggle initialTheme={initialTheme} />
            <LocaleToggle />
          </div>
        </div>
      </aside>
    </>
  );
}

/** `/` only matches itself; deeper routes match by prefix. */
function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

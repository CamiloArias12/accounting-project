import {
  ArrowRight,
  BookOpen,
  CalendarRange,
  ListTree,
  ReceiptText,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";

import { PageHeader, PageShell } from "@/components/PageHeader";

interface Card {
  href: string;
  titleKey: "accountsCard" | "thirdPartiesCard" | "vouchersCard" | "ledgerCard" | "periodsCard";
  hintKey:
    | "accountsCardHint"
    | "thirdPartiesCardHint"
    | "vouchersCardHint"
    | "ledgerCardHint"
    | "periodsCardHint";
  icon: LucideIcon;
}

const CARDS: Card[] = [
  {
    href: "/accounts",
    titleKey: "accountsCard",
    hintKey: "accountsCardHint",
    icon: ListTree,
  },
  {
    href: "/third-parties",
    titleKey: "thirdPartiesCard",
    hintKey: "thirdPartiesCardHint",
    icon: Users,
  },
  {
    href: "/vouchers",
    titleKey: "vouchersCard",
    hintKey: "vouchersCardHint",
    icon: ReceiptText,
  },
  {
    href: "/ledger",
    titleKey: "ledgerCard",
    hintKey: "ledgerCardHint",
    icon: BookOpen,
  },
  {
    href: "/periods",
    titleKey: "periodsCard",
    hintKey: "periodsCardHint",
    icon: CalendarRange,
  },
];

export default function Overview() {
  const t = useTranslations("overview");

  return (
    <PageShell>
      <PageHeader eyebrow={t("eyebrow")} title={t("title")} subtitle={t("subtitle")} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.href}
              href={card.href}
              className="group relative flex flex-col gap-3 overflow-hidden rounded-2xl bg-card p-5 shadow-xs ring-1 ring-border transition-all hover:-translate-y-0.5 hover:shadow-md hover:ring-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.07] to-transparent opacity-0 transition-opacity group-hover:opacity-100"
              />

              <span className="relative grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15 transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Icon className="size-5" />
              </span>

              <span className="relative flex flex-col gap-1">
                <span className="font-medium tracking-tight">
                  {t(card.titleKey)}
                </span>
                <span className="text-sm leading-snug text-muted-foreground">
                  {t(card.hintKey)}
                </span>
              </span>

              <span className="relative mt-auto inline-flex items-center gap-1 pt-1 text-sm font-medium text-primary">
                {t("open")}
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          );
        })}
      </div>
    </PageShell>
  );
}

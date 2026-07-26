import { useTranslations } from "next-intl";
import Link from "next/link";

export default function Overview() {
  const t = useTranslations("overview");

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="text-sm text-muted">{t("subtitle")}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/accounts"
          className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-accent"
        >
          <span className="text-sm font-medium">{t("accountsCard")}</span>
          <span className="text-sm text-muted">{t("accountsCardHint")}</span>
          <span className="mt-2 text-sm font-medium text-accent">
            {t("open")} →
          </span>
        </Link>

        <Link
          href="/third-parties"
          className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-accent"
        >
          <span className="text-sm font-medium">{t("thirdPartiesCard")}</span>
          <span className="text-sm text-muted">{t("thirdPartiesCardHint")}</span>
          <span className="mt-2 text-sm font-medium text-accent">
            {t("open")} →
          </span>
        </Link>

        <Link
          href="/vouchers"
          className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-accent"
        >
          <span className="text-sm font-medium">{t("vouchersCard")}</span>
          <span className="text-sm text-muted">{t("vouchersCardHint")}</span>
          <span className="mt-2 text-sm font-medium text-accent">
            {t("open")} →
          </span>
        </Link>
      </div>
    </main>
  );
}

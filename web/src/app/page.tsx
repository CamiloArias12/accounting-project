import { useTranslations } from "next-intl";
import Link from "next/link";

export default function Home() {
  const t = useTranslations("home");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-24">
      <div className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="mt-2 text-sm opacity-60">{t("subtitle")}</p>
      </div>

      <Link
        href="/accounts"
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white"
      >
        {t("goToAccounts")}
      </Link>
    </main>
  );
}

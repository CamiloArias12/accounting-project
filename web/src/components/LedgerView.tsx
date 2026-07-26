"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";

import { formatMoney } from "@/lib/money";
import type { AccountLedger, LedgerReport } from "@/types/voucher";

interface Props {
  report: LedgerReport;
  detail: AccountLedger | null;
  dateFrom: string;
  dateTo: string;
  loadError: string | null;
}

export function LedgerView({
  report,
  detail,
  dateFrom,
  dateTo,
  loadError,
}: Props) {
  const t = useTranslations("ledger");
  const router = useRouter();
  const params = useSearchParams();

  function go(changes: Record<string, string>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    router.push(`/ledger?${next}`);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {loadError}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border p-3">
        <label className="flex flex-col gap-1 text-sm">
          {t("from")}
          <input
            type="date"
            defaultValue={dateFrom}
            onChange={(event) => go({ date_from: event.target.value })}
            className="rounded-md border border-border bg-transparent px-3 py-1.5"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          {t("to")}
          <input
            type="date"
            defaultValue={dateTo}
            onChange={(event) => go({ date_to: event.target.value })}
            className="rounded-md border border-border bg-transparent px-3 py-1.5"
          />
        </label>
        {detail && (
          <button
            type="button"
            onClick={() => go({ account: "" })}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            {t("backToReport")}
          </button>
        )}
      </div>

      {detail ? (
        <AccountDetail detail={detail} />
      ) : (
        <Report report={report} onOpen={(code) => go({ account: code })} />
      )}
    </main>
  );
}

function Report({
  report,
  onOpen,
}: {
  report: LedgerReport;
  onOpen: (code: string) => void;
}) {
  const t = useTranslations("ledger");

  if (report.accounts.length === 0) {
    return (
      <p className="rounded-lg border border-border p-6 text-center text-sm text-muted-foreground">
        {t("empty")}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[44rem] text-sm">
        <thead className="bg-card text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left font-medium">{t("account")}</th>
            <th className="px-3 py-2 text-right font-medium">{t("opening")}</th>
            <th className="px-3 py-2 text-right font-medium">{t("debit")}</th>
            <th className="px-3 py-2 text-right font-medium">{t("credit")}</th>
            <th className="px-3 py-2 text-right font-medium">{t("closing")}</th>
          </tr>
        </thead>
        <tbody>
          {report.accounts.map((account) => (
            <tr
              key={account.code}
              onClick={() => onOpen(account.code)}
              className="cursor-pointer border-t border-border hover:bg-foreground/5"
            >
              <td className="px-3 py-2">
                <span className="font-mono text-xs">{account.code}</span>
                <span className="ml-2">{account.name}</span>
              </td>
              <Money value={account.opening_balance} />
              <Money value={account.debit} />
              <Money value={account.credit} />
              <Money value={account.closing_balance} strong />
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-border font-medium">
            <td className="px-3 py-2">{t("totals")}</td>
            <td />
            <Money value={report.totals.debit} />
            <Money value={report.totals.credit} />
            <td className="px-3 py-2 text-right">
              {/* The one check that covers every voucher behind it: if each
                  entry balanced, the books as a whole add up to nothing. */}
              <span
                className={
                  report.totals.is_balanced
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-red-700 dark:text-red-400"
                }
              >
                {report.totals.is_balanced
                  ? `✓ ${formatMoney(report.totals.balance)}`
                  : formatMoney(report.totals.balance)}
              </span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function AccountDetail({ detail }: { detail: AccountLedger }) {
  const t = useTranslations("ledger");

  return (
    <section className="flex flex-col gap-3">
      <header>
        <h2 className="text-lg font-semibold">
          <span className="font-mono text-sm">{detail.code}</span> {detail.name}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t("opening")}: {formatMoney(detail.opening_balance)} ·{" "}
          {t("closing")}: {formatMoney(detail.closing_balance)}
        </p>
      </header>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[48rem] text-sm">
          <thead className="bg-card text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left font-medium">{t("voucher")}</th>
              <th className="px-3 py-2 text-left font-medium">{t("date")}</th>
              <th className="px-3 py-2 text-left font-medium">
                {t("description")}
              </th>
              <th className="px-3 py-2 text-right font-medium">{t("debit")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("credit")}</th>
              <th className="px-3 py-2 text-right font-medium">
                {t("running")}
              </th>
            </tr>
          </thead>
          <tbody>
            {detail.entries.length === 0 && (
              <tr>
                <td colSpan={6} className="p-6 text-center text-sm text-muted-foreground">
                  {t("empty")}
                </td>
              </tr>
            )}
            {detail.entries.map((entry, index) => (
              <tr
                key={`${entry.voucher_id}-${index}`}
                className="border-t border-border"
              >
                <td className="px-3 py-2 font-mono text-xs">
                  #{entry.voucher_number}
                  {entry.reverses_voucher_id !== null && (
                    <span className="ml-1 text-muted-foreground">↩</span>
                  )}
                </td>
                <td className="px-3 py-2">{entry.date}</td>
                <td className="px-3 py-2">{entry.description}</td>
                <Money value={entry.debit} />
                <Money value={entry.credit} />
                <Money value={entry.running_balance} strong />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Money({ value, strong = false }: { value: string; strong?: boolean }) {
  return (
    <td
      className={`px-3 py-2 text-right tabular-nums ${
        strong ? "font-medium" : ""
      }`}
    >
      {formatMoney(value)}
    </td>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";

import { VoucherForm } from "@/components/VoucherForm";
import { formatMoney } from "@/lib/money";
import {
  VOUCHER_STATUSES,
  type Company,
  type Voucher,
} from "@/types/voucher";

interface Props {
  vouchers: Voucher[];
  selected: Voucher | null;
  company: Company;
  thirdPartyLabels: Record<number, string>;
  today: string;
  loadError: string | null;
  status: string;
  search: string;
}

/**
 * Selection lives in the URL, like the third parties screen: the form needs the
 * names of the third parties on its lines, and only the server can resolve
 * those.
 */
export function VouchersWorkspace({
  vouchers,
  selected,
  company,
  thirdPartyLabels,
  today,
  loadError,
  status,
  search,
}: Props) {
  const t = useTranslations("vouchers");
  const router = useRouter();
  const params = useSearchParams();

  function go(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "selected") next.delete("selected");
    router.push(`/vouchers?${next}`);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted">
            {t("count", { count: vouchers.length })}
          </p>
        </div>
        <button
          type="button"
          onClick={() => go("selected", "")}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground"
        >
          {t("newVoucher")}
        </button>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {loadError}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[22rem_1fr]">
        <section className="min-w-0 rounded-lg border border-border">
          <div className="flex flex-wrap gap-2 border-b border-border p-3">
            <input
              defaultValue={search}
              placeholder={t("searchPlaceholder")}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  go("search", (event.target as HTMLInputElement).value);
                }
              }}
              className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-1.5 text-sm"
            />
            <select
              value={status}
              onChange={(event) => go("status", event.target.value)}
              className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
            >
              <option value="">{t("allStatuses")}</option>
              {VOUCHER_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {t(`statuses.${value}`)}
                </option>
              ))}
            </select>
          </div>

          <ul className="max-h-[70vh] divide-y divide-border overflow-y-auto">
            {vouchers.length === 0 && (
              <li className="p-6 text-center text-sm text-muted">{t("empty")}</li>
            )}
            {vouchers.map((voucher) => (
              <li key={voucher.id}>
                <button
                  type="button"
                  onClick={() => go("selected", String(voucher.id))}
                  aria-current={voucher.id === selected?.id ? "true" : undefined}
                  className={`flex w-full flex-col gap-0.5 px-3 py-2 text-left text-sm transition-colors ${
                    voucher.id === selected?.id
                      ? "bg-accent/10"
                      : "hover:bg-foreground/5"
                  }`}
                >
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-xs">
                      {voucher.number !== null
                        ? `#${voucher.number}`
                        : t("statuses.Draft")}
                    </span>
                    <span className="tabular-nums">
                      {formatMoney(voucher.total_debit)}
                    </span>
                  </span>
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate">{voucher.description}</span>
                    <span className="shrink-0 text-xs text-muted">
                      {voucher.date}
                    </span>
                  </span>
                  {(voucher.is_reversed || voucher.is_reversal) && (
                    <span className="text-[10px] uppercase text-muted">
                      {voucher.is_reversal ? t("isReversal") : t("isReversed")}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="min-w-0 rounded-lg border border-border p-4">
          <VoucherForm
            // Remounting on a different selection resets the form without effects.
            key={selected?.id ?? "new"}
            voucher={selected}
            company={company}
            thirdPartyLabels={thirdPartyLabels}
            today={today}
            onCancel={() => go("selected", "")}
          />
        </section>
      </div>
    </main>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ledger-from">{t("from")}</Label>
          <Input
            id="ledger-from"
            type="date"
            defaultValue={dateFrom}
            onChange={(event) => go({ date_from: event.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ledger-to">{t("to")}</Label>
          <Input
            id="ledger-to"
            type="date"
            defaultValue={dateTo}
            onChange={(event) => go({ date_to: event.target.value })}
          />
        </div>
        {detail && (
          <Button variant="outline" onClick={() => go({ account: "" })}>
            {t("backToReport")}
          </Button>
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
      <Table className="min-w-[44rem]">
        <TableHeader>
          <TableRow>
            <TableHead>{t("account")}</TableHead>
            <TableHead className="text-right">{t("opening")}</TableHead>
            <TableHead className="text-right">{t("debit")}</TableHead>
            <TableHead className="text-right">{t("credit")}</TableHead>
            <TableHead className="text-right">{t("closing")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {report.accounts.map((account) => (
            <TableRow
              key={account.code}
              onClick={() => onOpen(account.code)}
              className="cursor-pointer border-t border-border hover:bg-foreground/5"
            >
              <TableCell className="">
                <span className="font-mono text-xs">{account.code}</span>
                <span className="ml-2">{account.name}</span>
              </TableCell>
              <Money value={account.opening_balance} />
              <Money value={account.debit} />
              <Money value={account.credit} />
              <Money value={account.closing_balance} strong />
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow className="border-t-2 border-border font-medium">
            <TableCell className="">{t("totals")}</TableCell>
            <TableCell />
            <Money value={report.totals.debit} />
            <Money value={report.totals.credit} />
            <TableCell className=" text-right">
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
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
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
        <Table className="min-w-[48rem]">
          <TableHeader>
            <TableRow>
              <TableHead>{t("voucher")}</TableHead>
              <TableHead>{t("date")}</TableHead>
              <TableHead>
                {t("description")}
              </TableHead>
              <TableHead className="text-right">{t("debit")}</TableHead>
              <TableHead className="text-right">{t("credit")}</TableHead>
              <TableHead className="text-right">
                {t("running")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {detail.entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {detail.entries.map((entry, index) => (
              <TableRow
                key={`${entry.voucher_id}-${index}`}
                className="border-t border-border"
              >
                <TableCell className=" font-mono text-xs">
                  #{entry.voucher_number}
                  {entry.reverses_voucher_id !== null && (
                    <span className="ml-1 text-muted-foreground">↩</span>
                  )}
                </TableCell>
                <TableCell className="">{entry.date}</TableCell>
                <TableCell className="">{entry.description}</TableCell>
                <Money value={entry.debit} />
                <Money value={entry.credit} />
                <Money value={entry.running_balance} strong />
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}

function Money({ value, strong = false }: { value: string; strong?: boolean }) {
  return (
    <TableCell
      className={`text-right tabular-nums ${strong ? "font-medium" : ""}`}
    >
      {formatMoney(value)}
    </TableCell>
  );
}

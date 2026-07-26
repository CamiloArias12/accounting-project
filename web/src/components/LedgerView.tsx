"use client";

import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";

import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
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
import { cn } from "@/lib/utils";
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
    <PageShell className="max-w-7xl">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("subtitle")}
      />

      {loadError && <LoadError message={loadError} />}

      <div className="flex flex-wrap items-end gap-3 rounded-xl bg-card p-3 shadow-xs ring-1 ring-border">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ledger-from">{t("from")}</Label>
          <Input
            id="ledger-from"
            type="date"
            defaultValue={dateFrom}
            className="w-40"
            onChange={(event) => go({ date_from: event.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ledger-to">{t("to")}</Label>
          <Input
            id="ledger-to"
            type="date"
            defaultValue={dateTo}
            className="w-40"
            onChange={(event) => go({ date_to: event.target.value })}
          />
        </div>
        {detail && (
          <Button variant="outline" onClick={() => go({ account: "" })}>
            <ArrowLeft />
            {t("backToReport")}
          </Button>
        )}
      </div>

      {detail ? (
        <AccountDetail detail={detail} />
      ) : (
        <Report report={report} onOpen={(code) => go({ account: code })} />
      )}
    </PageShell>
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
      <p className="rounded-xl bg-card p-12 text-center text-sm text-muted-foreground shadow-xs ring-1 ring-border">
        {t("empty")}
      </p>
    );
  }

  return (
    <TableCard minWidth="44rem">
      <TableHeader>
        <TableRow className="bg-muted/50 hover:bg-muted/50">
          <TableHead className="pl-4">{t("account")}</TableHead>
          <TableHead className="text-right">{t("opening")}</TableHead>
          <TableHead className="text-right">{t("debit")}</TableHead>
          <TableHead className="text-right">{t("credit")}</TableHead>
          <TableHead className="pr-4 text-right">{t("closing")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {report.accounts.map((account) => (
          <TableRow
            key={account.code}
            onClick={() => onOpen(account.code)}
            className="cursor-pointer"
          >
            <TableCell className="pl-4">
              <span className="font-mono text-xs text-muted-foreground">
                {account.code}
              </span>
              <span className="ml-2 font-medium">{account.name}</span>
            </TableCell>
            <Money value={account.opening_balance} />
            <Money value={account.debit} />
            <Money value={account.credit} />
            <Money value={account.closing_balance} strong className="pr-4" />
          </TableRow>
        ))}
      </TableBody>
      <TableFooter>
        <TableRow className="hover:bg-transparent">
          <TableCell className="pl-4 font-medium">{t("totals")}</TableCell>
          <TableCell />
          <Money value={report.totals.debit} strong />
          <Money value={report.totals.credit} strong />
          <TableCell className="pr-4 text-right">
            {/* The one check that covers every voucher behind it: if each
                entry balanced, the books as a whole add up to nothing. */}
            <span
              className={cn(
                "font-medium tabular-nums",
                report.totals.is_balanced ? "text-success" : "text-destructive",
              )}
            >
              {report.totals.is_balanced
                ? `✓ ${formatMoney(report.totals.balance)}`
                : formatMoney(report.totals.balance)}
            </span>
          </TableCell>
        </TableRow>
      </TableFooter>
    </TableCard>
  );
}

function AccountDetail({ detail }: { detail: AccountLedger }) {
  const t = useTranslations("ledger");

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-card p-4 shadow-xs ring-1 ring-border">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            <span className="font-mono text-sm text-muted-foreground">
              {detail.code}
            </span>{" "}
            {detail.name}
          </h2>
        </div>
        <dl className="flex gap-6">
          <Figure label={t("opening")} value={detail.opening_balance} />
          <Figure label={t("closing")} value={detail.closing_balance} strong />
        </dl>
      </header>

      <TableCard minWidth="48rem">
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            <TableHead className="pl-4">{t("voucher")}</TableHead>
            <TableHead>{t("date")}</TableHead>
            <TableHead>{t("description")}</TableHead>
            <TableHead className="text-right">{t("debit")}</TableHead>
            <TableHead className="text-right">{t("credit")}</TableHead>
            <TableHead className="pr-4 text-right">{t("running")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {detail.entries.length === 0 && (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={6}
                className="py-14 text-center text-muted-foreground"
              >
                {t("empty")}
              </TableCell>
            </TableRow>
          )}
          {detail.entries.map((entry, index) => (
            <TableRow key={`${entry.voucher_id}-${index}`}>
              <TableCell className="pl-4 font-mono text-xs text-muted-foreground">
                #{entry.voucher_number}
                {entry.reverses_voucher_id !== null && (
                  <span className="ml-1">↩</span>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {entry.date}
              </TableCell>
              <TableCell>{entry.description}</TableCell>
              <Money value={entry.debit} />
              <Money value={entry.credit} />
              <Money value={entry.running_balance} strong className="pr-4" />
            </TableRow>
          ))}
        </TableBody>
      </TableCard>
    </section>
  );
}

/** The card a table sits in: one elevation, one scroll container, one radius. */
function TableCard({
  minWidth,
  children,
}: {
  minWidth: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl bg-card shadow-sm ring-1 ring-border">
      <div className="scrollbar-slim overflow-x-auto">
        <Table style={{ minWidth }}>{children}</Table>
      </div>
    </div>
  );
}

function Figure({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div>
      <dt className="text-[0.7rem] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd
        className={cn(
          "tabular-nums",
          strong ? "text-base font-semibold" : "text-sm",
        )}
      >
        {formatMoney(value)}
      </dd>
    </div>
  );
}

function Money({
  value,
  strong = false,
  className,
}: {
  value: string;
  strong?: boolean;
  className?: string;
}) {
  return (
    <TableCell
      className={cn(
        "text-right tabular-nums",
        strong ? "font-medium" : "text-muted-foreground",
        className,
      )}
    >
      {formatMoney(value)}
    </TableCell>
  );
}

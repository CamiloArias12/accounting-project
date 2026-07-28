"use client";

import { ArrowLeft, Download } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useTransition } from "react";

import { searchAccounts, searchThirdParties } from "@/actions/lookups";
import { AsyncCombobox, type Option } from "@/components/AsyncCombobox";
import { DateField } from "@/components/DateField";
import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Button, buttonVariants } from "@/components/ui/button";
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
import { formatMoney, fromCents, sumCents } from "@/lib/money";
import { cn } from "@/lib/utils";
import type { AccountLedger } from "@/types/voucher";

interface Props {
  book: AccountLedger[];
  dateFrom: string;
  dateTo: string;
  // The account being read, and its name, so the picker reads well on load.
  account: string;
  accountLabel: string;
  thirdParty: string;
  thirdPartyLabel: string;
  loadError: string | null;
}

export function LedgerView({
  book,
  dateFrom,
  dateTo,
  account,
  accountLabel,
  thirdParty,
  thirdPartyLabel,
  loadError,
}: Props) {
  const t = useTranslations("ledger");
  const status = useTranslations("status");
  const router = useRouter();
  const params = useSearchParams();
  const [isLoading, startNavigation] = useTransition();

  function go(changes: Record<string, string>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    startNavigation(() => router.push(`/ledger?${next}`));
  }

  const accountOptions = useCallback(
    async (query: string): Promise<Option[]> =>
      (await searchAccounts(query)).map((found) => ({
        value: found.code,
        label: `${found.code} · ${found.name}`,
      })),
    [],
  );

  const thirdPartyOptions = useCallback(
    async (query: string): Promise<Option[]> =>
      (await searchThirdParties(query)).map((found) => ({
        value: String(found.id),
        label: found.full_name,
        hint: found.formatted_document,
      })),
    [],
  );

  return (
    <PageShell className="max-w-7xl">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <a
            href={`/ledger/export?${params}`}
            download
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            <Download />
            {t("downloadBook")}
          </a>
        }
      />

      {loadError && <LoadError message={loadError} />}

      <div className="flex flex-wrap items-end gap-3 rounded-xl bg-card p-3 shadow-xs ring-1 ring-border">
        <div className="flex w-40 flex-col gap-1.5">
          <Label>{t("from")}</Label>
          <DateField
            name="date_from"
            defaultValue={dateFrom}
            placeholder={t("anyDate")}
            onChange={(value) => go({ date_from: value })}
          />
        </div>
        <div className="flex w-40 flex-col gap-1.5">
          <Label>{t("to")}</Label>
          <DateField
            name="date_to"
            defaultValue={dateTo}
            placeholder={t("anyDate")}
            onChange={(value) => go({ date_to: value })}
          />
        </div>
        <div className="flex min-w-56 flex-1 flex-col gap-1.5">
          <Label>{t("account")}</Label>
          <AsyncCombobox
            value={account}
            selectedLabel={accountLabel}
            placeholder={t("wholeChart")}
            searchPlaceholder={t("accountSearch")}
            emptyLabel={t("noMatches")}
            search={accountOptions}
            onChange={(option) => go({ account: option?.value ?? "" })}
          />
        </div>

        <div className="flex min-w-56 flex-1 flex-col gap-1.5">
          <Label>{t("thirdParty")}</Label>
          <AsyncCombobox
            value={thirdParty}
            selectedLabel={thirdPartyLabel}
            placeholder={t("everyThirdParty")}
            searchPlaceholder={t("thirdPartySearch")}
            emptyLabel={t("noMatches")}
            search={thirdPartyOptions}
            onChange={(option) => go({ third_party: option?.value ?? "" })}
          />
        </div>

        {account && (
          <Button variant="outline" onClick={() => go({ account: "" })}>
            <ArrowLeft />
            {t("backToReport")}
          </Button>
        )}
      </div>

      <div
        aria-busy={isLoading}
        className={cn(
          "flex flex-col gap-6 transition-opacity",
          isLoading && "pointer-events-none opacity-50",
        )}
      >
        <span role="status" aria-live="polite" className="sr-only">
          {isLoading ? status("loading") : ""}
        </span>

        <Book book={book} onOpen={(code) => go({ account: code })} />
      </div>
    </PageShell>
  );
}

/** The whole book: every account with its movements, the same seven columns
 *  and the same layout the spreadsheet has. */
function Book({
  book,
  onOpen,
}: {
  book: AccountLedger[];
  onOpen: (code: string) => void;
}) {
  const t = useTranslations("ledger");

  if (book.length === 0) {
    return (
      <p className="rounded-xl bg-card p-12 text-center text-sm text-muted-foreground shadow-xs ring-1 ring-border">
        {t("empty")}
      </p>
    );
  }

  const debit = sumCents(book.map((account) => account.debit));
  const credit = sumCents(book.map((account) => account.credit));
  const balance = debit - credit;

  return (
    <div className="flex flex-col gap-4">
      {book.length > 1 && (
        <p className="text-xs text-muted-foreground">{t("openAnAccount")}</p>
      )}

      <TableCard minWidth="56rem">
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            <TableHead className="pl-4">{t("date")}</TableHead>
            <TableHead>{t("voucher")}</TableHead>
            <TableHead>{t("description")}</TableHead>
            <TableHead>{t("thirdParty")}</TableHead>
            <TableHead className="text-right">{t("debit")}</TableHead>
            <TableHead className="text-right">{t("credit")}</TableHead>
            <TableHead className="pr-4 text-right">{t("running")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {book.map((account) => (
            <Fragment key={account.code}>
              <TableRow
                onClick={() => onOpen(account.code)}
                className="cursor-pointer bg-muted/30"
              >
                <TableCell colSpan={7} className="pl-4">
                  <span className="font-mono text-xs text-muted-foreground">
                    {account.code}
                  </span>
                  <span className="ml-2 font-medium">{account.name}</span>
                </TableCell>
              </TableRow>

              {account.entries.map((entry, index) => (
                <TableRow key={`${account.code}-${entry.voucher_id}-${index}`}>
                  <TableCell className="pl-4 text-muted-foreground">
                    {entry.date}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{entry.voucher_number}
                    {entry.reverses_voucher_id !== null && (
                      <span className="ml-1">↩</span>
                    )}
                  </TableCell>
                  <TableCell>{entry.description}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {entry.third_party_name ?? "—"}
                  </TableCell>
                  <Money value={entry.debit} />
                  <Money value={entry.credit} />
                  <Money value={entry.running_balance} strong className="pr-4" />
                </TableRow>
              ))}

              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={3} />
                <TableCell className="font-medium">{t("totals")}</TableCell>
                <Money value={account.debit} strong />
                <Money value={account.credit} strong />
                <Money value={account.closing_balance} strong className="pr-4" />
              </TableRow>
            </Fragment>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow className="hover:bg-transparent">
            <TableCell colSpan={3} className="pl-4" />
            <TableCell className="font-medium">{t("grandTotal")}</TableCell>
            <Money value={fromCents(debit)} strong />
            <Money value={fromCents(credit)} strong />
            <TableCell className="pr-4 text-right">
              <span
                className={cn(
                  "font-medium tabular-nums",
                  balance === 0 ? "text-success" : "text-destructive",
                )}
              >
                {balance === 0
                  ? `✓ ${formatMoney(0)}`
                  : formatMoney(fromCents(balance))}
              </span>
            </TableCell>
          </TableRow>
        </TableFooter>
      </TableCard>
    </div>
  );
}

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

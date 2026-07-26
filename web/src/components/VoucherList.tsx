"use client";

import { Plus, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import { VOUCHER_STATUSES, type Voucher } from "@/types/voucher";

interface Props {
  vouchers: Voucher[];
  total: number;
  skip: number;
  limit: number;
  loadError: string | null;
  status: string;
  search: string;
}

/**
 * The list on its own page.
 *
 * Writing a voucher used to happen in a panel beside the list, which left the
 * entry — the part with six columns and any number of rows — in a third of the
 * screen. It has its own route now, and this page only lists.
 */
export function VoucherList({
  vouchers,
  total,
  skip,
  limit,
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
    // Any filter change goes back to the first page: page four of the old
    // list is not page four of the new one.
    if (key !== "skip") next.delete("skip");
    router.push(`/vouchers?${next}`);
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("count", { count: total })}
        actions={
          /* `nativeButton={false}`: this renders an <a>, and Base UI warns when
             something styled as a button is not one — the semantics differ. */
          <Button nativeButton={false} render={<Link href="/vouchers/new" />}>
            <Plus />
            {t("newVoucher")}
          </Button>
        }
      />

      {loadError && <LoadError message={loadError} />}

      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-card p-2 shadow-xs ring-1 ring-border">
        <div className="relative min-w-56 flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            defaultValue={search}
            placeholder={t("searchPlaceholder")}
            className="pl-8"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                go("search", (event.target as HTMLInputElement).value);
              }
            }}
          />
        </div>
        <SearchableSelect
          className="w-48"
          value={status || "all"}
          // "all" is the stand-in for no filter; an empty string clears the
          // query param rather than writing `status=all` into the URL.
          onChange={(value) => go("status", value === "all" ? "" : value)}
          options={[
            { value: "all", label: t("allStatuses") },
            ...VOUCHER_STATUSES.map((value) => ({
              value,
              label: t(`statuses.${value}`),
            })),
          ]}
        />
      </div>

      <div className="overflow-hidden rounded-xl bg-card shadow-sm ring-1 ring-border">
        <div className="scrollbar-slim overflow-x-auto">
          <Table className="min-w-[44rem]">
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="w-24 pl-4">{t("columnNumber")}</TableHead>
                <TableHead className="w-32">{t("columnDate")}</TableHead>
                <TableHead>{t("columnDescription")}</TableHead>
                <TableHead className="w-36 text-right">
                  {t("columnTotal")}
                </TableHead>
                <TableHead className="w-36 pr-4">{t("columnStatus")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {vouchers.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={5}
                    className="py-14 text-center text-muted-foreground"
                  >
                    {t("empty")}
                  </TableCell>
                </TableRow>
              )}
              {vouchers.map((voucher) => (
                <TableRow
                  key={voucher.id}
                  onClick={() => router.push(`/vouchers/${voucher.id}`)}
                  className="cursor-pointer"
                >
                  <TableCell className="pl-4 font-mono text-xs text-muted-foreground">
                    {voucher.number !== null ? `#${voucher.number}` : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {voucher.date}
                  </TableCell>
                  <TableCell className="font-medium">
                    {voucher.description}
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
                    {formatMoney(voucher.total_debit)}
                  </TableCell>
                  <TableCell className="pr-4">
                    <div className="flex flex-wrap gap-1">
                      <Badge
                        variant={
                          voucher.status === "Posted" ? "default" : "secondary"
                        }
                      >
                        {t(`statuses.${voucher.status}`)}
                      </Badge>
                      {voucher.is_reversal && (
                        <Badge variant="outline">{t("isReversal")}</Badge>
                      )}
                      {voucher.is_reversed && (
                        <Badge variant="outline">{t("isReversed")}</Badge>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <Pagination
        total={total}
        skip={skip}
        limit={limit}
        onChange={(next) => go("skip", next === 0 ? "" : String(next))}
      />
    </PageShell>
  );
}

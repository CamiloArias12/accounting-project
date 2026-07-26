"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
export function VoucherList({ vouchers, loadError, status, search }: Props) {
  const t = useTranslations("vouchers");
  const router = useRouter();
  const params = useSearchParams();

  function go(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    router.push(`/vouchers?${next}`);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("count", { count: vouchers.length })}
          </p>
        </div>
        {/* `nativeButton={false}`: this renders an <a>, and Base UI warns when
            something styled as a button is not one — the semantics differ. */}
        <Button nativeButton={false} render={<Link href="/vouchers/new" />}>
          <Plus />
          {t("newVoucher")}
        </Button>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {loadError}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Input
          defaultValue={search}
          placeholder={t("searchPlaceholder")}
          className="max-w-xs"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              go("search", (event.target as HTMLInputElement).value);
            }
          }}
        />
        <Select
          value={status || "all"}
          // Base UI hands back null when the value is cleared; "all" is our
          // stand-in for no filter, and an empty string clears the query param.
          onValueChange={(value) =>
            go("status", !value || value === "all" ? "" : String(value))
          }
        >
          <SelectTrigger className="w-48">
            {/* Base UI's Value renders the raw value; the label has to be
                spelled out, and "all" is our stand-in for no filter. */}
            <SelectValue>
              {(value: string) =>
                value === "all" ? t("allStatuses") : t(`statuses.${value}`)
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("allStatuses")}</SelectItem>
            {VOUCHER_STATUSES.map((value) => (
              <SelectItem key={value} value={value}>
                {t(`statuses.${value}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <Table className="min-w-[44rem]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">{t("columnNumber")}</TableHead>
              <TableHead className="w-32">{t("columnDate")}</TableHead>
              <TableHead>{t("columnDescription")}</TableHead>
              <TableHead className="w-36 text-right">
                {t("columnTotal")}
              </TableHead>
              <TableHead className="w-36">{t("columnStatus")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {vouchers.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-10 text-center text-muted-foreground"
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
                <TableCell className="font-mono text-xs">
                  {voucher.number !== null ? `#${voucher.number}` : "—"}
                </TableCell>
                <TableCell>{voucher.date}</TableCell>
                <TableCell>{voucher.description}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(voucher.total_debit)}
                </TableCell>
                <TableCell>
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
    </main>
  );
}

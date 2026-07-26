"use client";

import { Check, Plus, TriangleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";

import { searchAccounts, searchThirdParties } from "@/actions/lookups";
import { AsyncCombobox, type Option } from "@/components/AsyncCombobox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney, fromCents, sumCents, toCents } from "@/lib/money";
import type { VoucherLine } from "@/types/voucher";

export interface DraftLine {
  key: string;
  account_code: string;
  account_label: string;
  third_party_id: number | null;
  third_party_label: string;
  debit: string;
  credit: string;
  description: string;
}

interface Props {
  initial: VoucherLine[];
  readOnly: boolean;
  labels: Record<number, string>;
}

let nextKey = 0;

function blank(): DraftLine {
  nextKey += 1;
  return {
    key: `line-${nextKey}`,
    account_code: "",
    account_label: "",
    third_party_id: null,
    third_party_label: "",
    debit: "",
    credit: "",
    description: "",
  };
}

/**
 * The entry itself: rows in, two totals out.
 *
 * The totals are added in cents, never as floating point numbers — the server
 * refuses an entry that is off by a hundredth, so the figure the user is
 * watching has to be the same one it will check.
 */
export function VoucherLines({ initial, readOnly, labels }: Props) {
  const t = useTranslations("voucherForm");

  const [lines, setLines] = useState<DraftLine[]>(() =>
    initial.length > 0
      ? initial.map((line, index) => ({
          key: `stored-${line.id ?? index}`,
          account_code: line.account_code,
          account_label: line.account_code,
          third_party_id: line.third_party_id,
          third_party_label: line.third_party_id
            ? (labels[line.third_party_id] ?? String(line.third_party_id))
            : "",
          debit: line.debit === "0.00" ? "" : line.debit,
          credit: line.credit === "0.00" ? "" : line.credit,
          description: line.description ?? "",
        }))
      : [blank(), blank()],
  );

  const accountOptions = useCallback(
    async (query: string): Promise<Option[]> =>
      (await searchAccounts(query)).map((account) => ({
        value: account.code,
        label: `${account.code} · ${account.name}`,
        hint: account.requires_third_party ? t("needsThirdParty") : undefined,
      })),
    [t],
  );

  const thirdPartyOptions = useCallback(
    async (query: string): Promise<Option[]> =>
      (await searchThirdParties(query)).map((thirdParty) => ({
        value: String(thirdParty.id),
        label: thirdParty.full_name,
        hint: thirdParty.formatted_document,
      })),
    [],
  );

  const totals = useMemo(() => {
    const debit = sumCents(lines.map((line) => line.debit));
    const credit = sumCents(lines.map((line) => line.credit));
    return { debit, credit, difference: debit - credit };
  }, [lines]);

  function update(key: string, changes: Partial<DraftLine>) {
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...changes } : line)),
    );
  }

  // The payload the action reads: only what the API wants, none of the labels.
  const payload = lines
    .filter((line) => line.account_code)
    .map((line) => ({
      account_code: line.account_code,
      third_party_id: line.third_party_id,
      debit: fromCents(toCents(line.debit)),
      credit: fromCents(toCents(line.credit)),
      description: line.description,
    }));

  return (
    <div className="flex flex-col gap-3">
      <input type="hidden" name="lines" value={JSON.stringify(payload)} />

      <div className="scrollbar-slim overflow-x-auto rounded-xl ring-1 ring-border">
        <Table className="min-w-[54rem]">
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead className="w-[26%] pl-3">{t("account")}</TableHead>
              <TableHead className="w-[22%]">{t("thirdParty")}</TableHead>
              <TableHead className="w-[15%] text-right">{t("debit")}</TableHead>
              <TableHead className="w-[15%] text-right">
                {t("credit")}
              </TableHead>
              <TableHead>{t("lineNote")}</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {lines.map((line) => (
              <TableRow key={line.key} className="hover:bg-transparent">
                <TableCell className="pl-3">
                  <AsyncCombobox
                    value={line.account_code}
                    selectedLabel={line.account_label}
                    placeholder={t("accountPlaceholder")}
                    searchPlaceholder={t("accountSearch")}
                    emptyLabel={t("noMatches")}
                    disabled={readOnly}
                    search={accountOptions}
                    onChange={(option) =>
                      update(line.key, {
                        account_code: option?.value ?? "",
                        account_label: option?.label ?? "",
                      })
                    }
                  />
                </TableCell>
                <TableCell>
                  <AsyncCombobox
                    value={
                      line.third_party_id ? String(line.third_party_id) : ""
                    }
                    selectedLabel={line.third_party_label}
                    placeholder={t("thirdPartyPlaceholder")}
                    searchPlaceholder={t("thirdPartySearch")}
                    emptyLabel={t("noMatches")}
                    disabled={readOnly}
                    search={thirdPartyOptions}
                    onChange={(option) =>
                      update(line.key, {
                        third_party_id: option ? Number(option.value) : null,
                        third_party_label: option?.label ?? "",
                      })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    value={line.debit}
                    readOnly={readOnly}
                    inputMode="decimal"
                    placeholder="0.00"
                    className="text-right tabular-nums"
                    onChange={(event) =>
                      // One column or the other, never both: the server refuses
                      // a line that carries two.
                      update(line.key, {
                        debit: event.target.value,
                        credit: "",
                      })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    value={line.credit}
                    readOnly={readOnly}
                    inputMode="decimal"
                    placeholder="0.00"
                    className="text-right tabular-nums"
                    onChange={(event) =>
                      update(line.key, {
                        credit: event.target.value,
                        debit: "",
                      })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    value={line.description}
                    readOnly={readOnly}
                    onChange={(event) =>
                      update(line.key, { description: event.target.value })
                    }
                  />
                </TableCell>
                <TableCell>
                  {!readOnly && lines.length > 2 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-xs"
                      aria-label={t("removeLine")}
                      onClick={() =>
                        setLines((current) =>
                          current.filter((row) => row.key !== line.key),
                        )
                      }
                    >
                      <X />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={2} className="pl-3">
                {t("totals")}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatMoney(totals.debit)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatMoney(totals.credit)}
              </TableCell>
              <TableCell colSpan={2}>
                <Difference cents={totals.difference} />
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      </div>

      {!readOnly && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => setLines((current) => [...current, blank()])}
        >
          <Plus />
          {t("addLine")}
        </Button>
      )}
    </div>
  );
}

function Difference({ cents }: { cents: number }) {
  const t = useTranslations("voucherForm");

  if (cents === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-xs font-medium text-success">
        <Check className="size-3.5" />
        {t("balanced")}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
      <TriangleAlert className="size-3.5" />
      {t("offBy", { amount: formatMoney(Math.abs(cents)) })}
    </span>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";

import { searchAccounts, searchThirdParties } from "@/actions/lookups";
import { SearchSelect, type Option } from "@/components/SearchSelect";
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

      <div className="overflow-x-auto">
        <table className="w-full min-w-[52rem] text-sm">
          <thead className="text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="w-[26%] px-2 py-1 text-left font-medium">
                {t("account")}
              </th>
              <th className="w-[22%] px-2 py-1 text-left font-medium">
                {t("thirdParty")}
              </th>
              <th className="w-[16%] px-2 py-1 text-right font-medium">
                {t("debit")}
              </th>
              <th className="w-[16%] px-2 py-1 text-right font-medium">
                {t("credit")}
              </th>
              <th className="px-2 py-1 text-left font-medium">{t("lineNote")}</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.key} className="border-t border-border align-top">
                <td className="px-2 py-1.5">
                  <SearchSelect
                    value={line.account_code}
                    selectedLabel={line.account_label}
                    placeholder={t("accountPlaceholder")}
                    disabled={readOnly}
                    required
                    search={accountOptions}
                    onChange={(option) =>
                      update(line.key, {
                        account_code: option?.value ?? "",
                        account_label: option?.label ?? "",
                      })
                    }
                  />
                </td>
                <td className="px-2 py-1.5">
                  <SearchSelect
                    value={line.third_party_id ? String(line.third_party_id) : ""}
                    selectedLabel={line.third_party_label}
                    placeholder={t("thirdPartyPlaceholder")}
                    disabled={readOnly}
                    search={thirdPartyOptions}
                    onChange={(option) =>
                      update(line.key, {
                        third_party_id: option ? Number(option.value) : null,
                        third_party_label: option?.label ?? "",
                      })
                    }
                  />
                </td>
                <td className="px-2 py-1.5">
                  <Amount
                    value={line.debit}
                    readOnly={readOnly}
                    onChange={(value) =>
                      // One column or the other, never both: the server
                      // refuses a line that carries two.
                      update(line.key, { debit: value, credit: "" })
                    }
                  />
                </td>
                <td className="px-2 py-1.5">
                  <Amount
                    value={line.credit}
                    readOnly={readOnly}
                    onChange={(value) =>
                      update(line.key, { credit: value, debit: "" })
                    }
                  />
                </td>
                <td className="px-2 py-1.5">
                  <input
                    value={line.description}
                    readOnly={readOnly}
                    onChange={(event) =>
                      update(line.key, { description: event.target.value })
                    }
                    className="w-full rounded-md border border-border bg-transparent px-2 py-1.5 text-sm read-only:opacity-60"
                  />
                </td>
                <td className="px-1 py-1.5">
                  {!readOnly && lines.length > 2 && (
                    <button
                      type="button"
                      aria-label={t("removeLine")}
                      onClick={() =>
                        setLines((current) =>
                          current.filter((row) => row.key !== line.key),
                        )
                      }
                      className="rounded px-2 py-1 text-muted hover:bg-foreground/5"
                    >
                      ×
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-border font-medium">
              <td className="px-2 py-2" colSpan={2}>
                {t("totals")}
              </td>
              <td className="px-2 py-2 text-right tabular-nums">
                {formatMoney(totals.debit)}
              </td>
              <td className="px-2 py-2 text-right tabular-nums">
                {formatMoney(totals.credit)}
              </td>
              <td className="px-2 py-2" colSpan={2}>
                <Difference cents={totals.difference} />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {!readOnly && (
        <button
          type="button"
          onClick={() => setLines((current) => [...current, blank()])}
          className="self-start rounded-md border border-border px-3 py-1.5 text-sm"
        >
          {t("addLine")}
        </button>
      )}
    </div>
  );
}

function Difference({ cents }: { cents: number }) {
  const t = useTranslations("voucherForm");

  if (cents === 0) {
    return (
      <span className="text-sm text-emerald-700 dark:text-emerald-400">
        ✓ {t("balanced")}
      </span>
    );
  }

  return (
    <span className="text-sm text-red-700 dark:text-red-400">
      {t("offBy", { amount: formatMoney(Math.abs(cents)) })}
    </span>
  );
}

function Amount({
  value,
  readOnly,
  onChange,
}: {
  value: string;
  readOnly: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <input
      value={value}
      readOnly={readOnly}
      inputMode="decimal"
      placeholder="0.00"
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-md border border-border bg-transparent px-2 py-1.5 text-right text-sm tabular-nums read-only:opacity-60"
    />
  );
}

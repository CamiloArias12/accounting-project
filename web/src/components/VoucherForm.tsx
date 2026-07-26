"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import {
  discardVoucher,
  postOrReverseVoucher,
  saveVoucher,
} from "@/actions/vouchers";
import { VoucherLines } from "@/components/VoucherLines";
import { formatMoney } from "@/lib/money";
import type { Company, Voucher } from "@/types/voucher";

interface Props {
  /**
   * The voucher being worked on; absent when writing a new one.
   *
   * The parent remounts this with `key` when the selection changes, so plain
   * `defaultValue`s are enough — no effect syncing state to props.
   */
  voucher: Voucher | null;
  company: Company;
  /** Names of the third parties named on the lines, so the pickers read well. */
  thirdPartyLabels: Record<number, string>;
  today: string;
  onCancel: () => void;
}

export function VoucherForm({
  voucher,
  company,
  thirdPartyLabels,
  today,
  onCancel,
}: Props) {
  const t = useTranslations("voucherForm");

  const isEditing = voucher !== null;
  // A posted voucher is an accounting record: it is shown, never edited.
  const readOnly = voucher?.status === "Posted";

  const [state, submit] = useActionState<FormState, FormData>(saveVoucher, IDLE);
  const [lifecycle, submitLifecycle] = useActionState<FormState, FormData>(
    postOrReverseVoucher,
    IDLE,
  );
  const [discard, submitDiscard] = useActionState<FormState, FormData>(
    discardVoucher,
    IDLE,
  );

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {isEditing
              ? voucher.number !== null
                ? t("editTitleNumbered", { number: voucher.number })
                : t("editTitle")
              : t("createTitle")}
          </h2>
          {/* The company is configuration, not a field: there is nothing to
              choose, so it is printed rather than asked for. */}
          <p className="text-xs text-muted-foreground">
            {company.legal_name} · {company.nit}
          </p>
        </div>
        {isEditing && <StatusBadge voucher={voucher} />}
      </header>

      <form action={submit} className="flex flex-col gap-4">
        {isEditing && <input type="hidden" name="id" value={voucher.id} />}

        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_2fr]">
          <label className="flex flex-col gap-1 text-sm">
            {t("date")}
            <input
              name="date"
              type="date"
              defaultValue={voucher?.date ?? today}
              readOnly={readOnly}
              required
              className="rounded-md border border-border bg-transparent px-3 py-2 read-only:opacity-60"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t("period")}
            <div className="flex gap-1">
              <input
                name="period_year"
                type="number"
                defaultValue={voucher?.period_year ?? ""}
                placeholder={t("fromDate")}
                readOnly={readOnly}
                className="w-20 rounded-md border border-border bg-transparent px-2 py-2 read-only:opacity-60"
              />
              <input
                name="period_month"
                type="number"
                min={1}
                max={12}
                defaultValue={voucher?.period_month ?? ""}
                placeholder="MM"
                readOnly={readOnly}
                className="w-16 rounded-md border border-border bg-transparent px-2 py-2 read-only:opacity-60"
              />
            </div>
            <span className="text-xs text-muted-foreground">{t("periodHint")}</span>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t("description")}
            <input
              name="description"
              defaultValue={voucher?.description ?? ""}
              readOnly={readOnly}
              required
              className="rounded-md border border-border bg-transparent px-3 py-2 read-only:opacity-60"
            />
          </label>
        </div>

        <VoucherLines
          initial={voucher?.lines ?? []}
          readOnly={readOnly}
          labels={thirdPartyLabels}
        />

        <Feedback state={state} />

        {!readOnly && (
          <div className="flex flex-wrap gap-2">
            <Submit label={t("save")} pendingLabel={t("saving")} primary />
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md border border-border px-4 py-2 text-sm"
            >
              {t("cancel")}
            </button>
          </div>
        )}
      </form>

      {isEditing && (
        <div className="flex flex-col gap-3 border-t border-border pt-4">
          <Feedback state={lifecycle} />
          <Feedback state={discard} />

          <div className="flex flex-wrap items-center gap-2">
            {!readOnly && (
              <>
                <form action={submitLifecycle}>
                  <input type="hidden" name="id" value={voucher.id} />
                  <input type="hidden" name="intent" value="post" />
                  <Submit label={t("post")} pendingLabel={t("posting")} primary />
                </form>
                <form action={submitDiscard}>
                  <input type="hidden" name="id" value={voucher.id} />
                  <Submit label={t("discard")} pendingLabel={t("discarding")} danger />
                </form>
              </>
            )}

            {readOnly && !voucher.is_reversed && !voucher.is_reversal && (
              <form action={submitLifecycle} className="flex items-end gap-2">
                <input type="hidden" name="id" value={voucher.id} />
                <input type="hidden" name="intent" value="reverse" />
                <input
                  type="hidden"
                  name="description"
                  value={t("reversalOf", { number: voucher.number ?? "" })}
                />
                <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                  {t("reversalDate")}
                  <input
                    name="date"
                    type="date"
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
                  />
                </label>
                <Submit label={t("reverse")} pendingLabel={t("reversing")} danger />
              </form>
            )}
          </div>

          {readOnly && (
            <p className="text-xs text-muted-foreground">
              {voucher.is_reversal
                ? t("isReversalNotice", {
                    number: voucher.reverses_voucher_id ?? "",
                  })
                : voucher.is_reversed
                  ? t("isReversedNotice")
                  : t("postedNotice")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ voucher }: { voucher: Voucher }) {
  const t = useTranslations("vouchers");

  const tone =
    voucher.status === "Posted"
      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      : "bg-foreground/10 text-muted-foreground";

  return (
    <div className="flex flex-col items-end gap-1">
      <span className={`rounded px-2 py-0.5 text-xs uppercase ${tone}`}>
        {t(`statuses.${voucher.status}`)}
      </span>
      <span className="text-xs tabular-nums text-muted-foreground">
        {formatMoney(voucher.total_debit)}
      </span>
    </div>
  );
}

function Feedback({ state }: { state: FormState }) {
  if (state.status === "idle") return null;

  const isError = state.status === "error";
  return (
    <p
      role={isError ? "alert" : "status"}
      className={`rounded-md px-3 py-2 text-sm ${
        isError
          ? "bg-red-500/10 text-red-700 dark:text-red-400"
          : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      }`}
    >
      {state.message}
    </p>
  );
}

function Submit({
  label,
  pendingLabel,
  primary = false,
  danger = false,
}: {
  label: string;
  pendingLabel: string;
  primary?: boolean;
  danger?: boolean;
}) {
  const { pending } = useFormStatus();

  const tone = primary
    ? "bg-primary text-primary-foreground"
    : danger
      ? "text-red-600 hover:bg-red-500/10 dark:text-red-400"
      : "border border-border";

  return (
    <button
      type="submit"
      disabled={pending}
      className={`rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50 ${tone}`}
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

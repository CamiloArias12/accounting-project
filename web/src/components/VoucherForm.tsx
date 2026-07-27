"use client";

import { ReceiptText } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";
import { toast } from "sonner";

import { IDLE, type FormState } from "@/actions/state";
import {
  discardVoucher,
  postOrReverseVoucher,
  saveVoucher,
} from "@/actions/vouchers";
import { DateField } from "@/components/DateField";
import { VoucherLines } from "@/components/VoucherLines";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { formatMoney } from "@/lib/money";
import type { Company, Voucher } from "@/types/voucher";

interface Props {
  // The voucher being worked on; absent when writing a new one.
  voucher: Voucher | null;
  company: Company;
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

  useAnnounce(state);
  useAnnounce(lifecycle);
  useAnnounce(discard);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15"
          >
            <ReceiptText className="size-5" />
          </span>
          <div>
            <h2 className="text-lg font-semibold tracking-tight">
              {isEditing
                ? voucher.number !== null
                  ? t("editTitleNumbered", { number: voucher.number })
                  : t("editTitle")
                : t("createTitle")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {company.legal_name} · {company.nit}
            </p>
          </div>
        </div>
        {isEditing && (
          <div className="flex flex-col items-end gap-1">
            <Badge variant={readOnly ? "default" : "secondary"}>
              {t(`statuses.${voucher.status}`)}
            </Badge>
            <span className="text-sm font-medium tabular-nums">
              {formatMoney(voucher.total_debit)}
            </span>
          </div>
        )}
      </header>

      <Separator />

      <form action={submit} className="flex flex-col gap-4">
        {isEditing && <input type="hidden" name="id" value={voucher.id} />}

        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_2fr]">
          <div className="flex flex-col gap-1.5">
            <Label>{t("date")}</Label>
            <DateField
              name="date"
              defaultValue={voucher?.date ?? today}
              placeholder={t("pickDate")}
              readOnly={readOnly}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>{t("period")}</Label>
            <div className="flex gap-1">
              <Input
                name="period_year"
                type="number"
                defaultValue={voucher?.period_year ?? ""}
                placeholder={t("fromDate")}
                readOnly={readOnly}
                className="w-20"
              />
              <Input
                name="period_month"
                type="number"
                min={1}
                max={12}
                defaultValue={voucher?.period_month ?? ""}
                placeholder="MM"
                readOnly={readOnly}
                className="w-16"
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {t("periodHint")}
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="voucher-description">{t("description")}</Label>
            <Input
              id="voucher-description"
              name="description"
              defaultValue={voucher?.description ?? ""}
              readOnly={readOnly}
              required
            />
          </div>
        </div>

        <VoucherLines
          initial={voucher?.lines ?? []}
          readOnly={readOnly}
          labels={thirdPartyLabels}
        />

        {!readOnly && (
          <div className="flex flex-wrap gap-2">
            <Submit label={t("save")} pendingLabel={t("saving")} />
            <Button type="button" variant="outline" onClick={onCancel}>
              {t("cancel")}
            </Button>
          </div>
        )}
      </form>

      {isEditing && (
        <>
          <Separator />
          <div className="flex flex-wrap items-center gap-2">
            {!readOnly && (
              <>
                <form action={submitLifecycle}>
                  <input type="hidden" name="id" value={voucher.id} />
                  <input type="hidden" name="intent" value="post" />
                  <Submit label={t("post")} pendingLabel={t("posting")} />
                </form>
                <form action={submitDiscard}>
                  <input type="hidden" name="id" value={voucher.id} />
                  <Submit
                    label={t("discard")}
                    pendingLabel={t("discarding")}
                    variant="destructive"
                  />
                </form>
              </>
            )}

            {readOnly && !voucher.is_reversed && !voucher.is_reversal && (
              <ReverseDialog voucher={voucher} action={submitLifecycle} />
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
        </>
      )}
    </div>
  );
}

function ReverseDialog({
  voucher,
  action,
}: {
  voucher: Voucher;
  action: (formData: FormData) => void;
}) {
  const t = useTranslations("voucherForm");

  return (
    <AlertDialog>
      <AlertDialogTrigger
        render={<Button variant="destructive">{t("reverse")}</Button>}
      />
      <AlertDialogContent>
        <form action={action}>
          <input type="hidden" name="id" value={voucher.id} />
          <input type="hidden" name="intent" value="reverse" />
          <input
            type="hidden"
            name="description"
            value={t("reversalOf", { number: voucher.number ?? "" })}
          />

          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("reverseTitle", { number: voucher.number ?? "" })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("reverseExplanation")}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="my-4 flex flex-col gap-1.5">
            <Label>{t("reversalDate")}</Label>
            <DateField name="date" placeholder={t("reversalDateHint")} />
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction type="submit">{t("reverse")}</AlertDialogAction>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function useAnnounce(state: FormState) {
  useEffect(() => {
    if (state.status === "success") toast.success(state.message);
    if (state.status === "error") toast.error(state.message);
  }, [state]);
}

function Submit({
  label,
  pendingLabel,
  variant = "default",
}: {
  label: string;
  pendingLabel: string;
  variant?: "default" | "destructive" | "outline";
}) {
  const { pending } = useFormStatus();

  return (
    <Button type="submit" variant={variant} disabled={pending}>
      {pending ? pendingLabel : label}
    </Button>
  );
}

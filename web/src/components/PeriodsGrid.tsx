"use client";

import { ChevronLeft, ChevronRight, Lock, LockOpen } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import { changePeriodState } from "@/actions/vouchers";
import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Period } from "@/types/voucher";

interface Props {
  year: number;
  periods: Period[];
  loadError: string | null;
}

export function PeriodsGrid({ year, periods, loadError }: Props) {
  const t = useTranslations("periods");
  const router = useRouter();
  const [state, submit] = useActionState<FormState, FormData>(
    changePeriodState,
    IDLE,
  );

  useEffect(() => {
    if (state.status === "success") toast.success(state.message);
    if (state.status === "error") toast.error(state.message);
  }, [state]);

  return (
    <PageShell className="max-w-5xl">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <div className="flex items-center gap-1 rounded-lg bg-card p-1 shadow-xs ring-1 ring-border">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("previousYear")}
              onClick={() => router.push(`/periods?year=${year - 1}`)}
            >
              <ChevronLeft />
            </Button>
            <span className="min-w-14 text-center text-sm font-semibold tabular-nums">
              {year}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("nextYear")}
              onClick={() => router.push(`/periods?year=${year + 1}`)}
            >
              <ChevronRight />
            </Button>
          </div>
        }
      />

      {loadError && <LoadError message={loadError} />}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {periods.map((period) => {
          const closed = period.status === "Closed";
          return (
            <form key={period.month} action={submit}>
              <input type="hidden" name="year" value={period.year} />
              <input type="hidden" name="month" value={period.month} />
              <input
                type="hidden"
                name="intent"
                value={closed ? "reopen" : "close"}
              />

              <div
                className={cn(
                  "flex items-center justify-between gap-3 rounded-xl p-4 shadow-xs ring-1 transition-shadow hover:shadow-sm",
                  closed
                    ? "bg-muted/50 ring-border"
                    : "bg-card ring-border",
                )}
              >
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className={cn(
                      "grid size-9 shrink-0 place-items-center rounded-lg",
                      closed
                        ? "bg-foreground/5 text-muted-foreground"
                        : "bg-success/10 text-success",
                    )}
                  >
                    {closed ? (
                      <Lock className="size-4" />
                    ) : (
                      <LockOpen className="size-4" />
                    )}
                  </span>
                  <div className="flex flex-col items-start gap-1">
                    <p className="text-sm font-medium">
                      {t(`months.${period.month}`)}
                    </p>
                    <Badge variant={closed ? "secondary" : "outline"}>
                      {t(`statuses.${period.status}`)}
                    </Badge>
                  </div>
                </div>

                <Action
                  label={closed ? t("reopen") : t("close")}
                  pendingLabel={closed ? t("reopening") : t("closing")}
                  closed={closed}
                />
              </div>
            </form>
          );
        })}
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">
        {t("hint")}
      </p>
    </PageShell>
  );
}

function Action({
  label,
  pendingLabel,
  closed,
}: {
  label: string;
  pendingLabel: string;
  closed: boolean;
}) {
  const { pending } = useFormStatus();

  return (
    <Button
      type="submit"
      variant={closed ? "outline" : "secondary"}
      size="sm"
      disabled={pending}
    >
      {pending ? pendingLabel : label}
    </Button>
  );
}

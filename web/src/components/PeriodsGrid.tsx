"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import { changePeriodState } from "@/actions/vouchers";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            aria-label={t("previousYear")}
            onClick={() => router.push(`/periods?year=${year - 1}`)}
          >
            <ChevronLeft />
          </Button>
          <span className="text-lg font-semibold tabular-nums">{year}</span>
          <Button
            variant="outline"
            size="icon"
            aria-label={t("nextYear")}
            onClick={() => router.push(`/periods?year=${year + 1}`)}
          >
            <ChevronRight />
          </Button>
        </div>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {loadError}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {periods.map((period) => {
          const closed = period.status === "Closed";
          return (
            <form key={period.month} action={submit}>
              <Card>
                <CardContent className="flex items-center justify-between gap-3">
              <input type="hidden" name="year" value={period.year} />
              <input type="hidden" name="month" value={period.month} />
              <input
                type="hidden"
                name="intent"
                value={closed ? "reopen" : "close"}
              />

                <div className="flex flex-col items-start gap-1">
                  <p className="text-sm font-medium">
                    {t(`months.${period.month}`)}
                  </p>
                  <Badge variant={closed ? "secondary" : "outline"}>
                    {t(`statuses.${period.status}`)}
                  </Badge>
                </div>

                <Action
                  label={closed ? t("reopen") : t("close")}
                  pendingLabel={closed ? t("reopening") : t("closing")}
                  closed={closed}
                />
                </CardContent>
              </Card>
            </form>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground">{t("hint")}</p>
    </main>
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
      variant={closed ? "outline" : "default"}
      size="sm"
      disabled={pending}
    >
      {pending ? pendingLabel : label}
    </Button>
  );
}

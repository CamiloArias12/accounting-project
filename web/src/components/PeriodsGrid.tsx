"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import { changePeriodState } from "@/actions/vouchers";
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

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.push(`/periods?year=${year - 1}`)}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            ←
          </button>
          <span className="text-lg font-semibold tabular-nums">{year}</span>
          <button
            type="button"
            onClick={() => router.push(`/periods?year=${year + 1}`)}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            →
          </button>
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

      {state.status !== "idle" && (
        <p
          role={state.status === "error" ? "alert" : "status"}
          className={`rounded-md px-3 py-2 text-sm ${
            state.status === "error"
              ? "bg-red-500/10 text-red-700 dark:text-red-400"
              : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
          }`}
        >
          {state.message}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {periods.map((period) => {
          const closed = period.status === "Closed";
          return (
            <form
              key={period.month}
              action={submit}
              className={`flex items-center justify-between gap-3 rounded-lg border p-4 ${
                closed ? "border-border bg-card" : "border-border"
              }`}
            >
              <input type="hidden" name="year" value={period.year} />
              <input type="hidden" name="month" value={period.month} />
              <input
                type="hidden"
                name="intent"
                value={closed ? "reopen" : "close"}
              />

              <div>
                <p className="text-sm font-medium">
                  {t(`months.${period.month}`)}
                </p>
                <p
                  className={`text-xs ${
                    closed
                      ? "text-muted-foreground"
                      : "text-emerald-700 dark:text-emerald-400"
                  }`}
                >
                  {t(`statuses.${period.status}`)}
                </p>
              </div>

              <Action
                label={closed ? t("reopen") : t("close")}
                pendingLabel={closed ? t("reopening") : t("closing")}
                closed={closed}
              />
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
    <button
      type="submit"
      disabled={pending}
      className={`rounded-md px-3 py-1.5 text-sm disabled:opacity-50 ${
        closed
          ? "border border-border"
          : "bg-primary text-primary-foreground font-medium"
      }`}
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

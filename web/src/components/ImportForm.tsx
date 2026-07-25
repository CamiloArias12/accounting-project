"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IMPORT_IDLE, type ImportState } from "@/app/accounts/action-state";
import { importAccounts } from "@/app/accounts/actions";
import type { ImportResult } from "@/types/account";

export function ImportForm() {
  const t = useTranslations("import");
  const [state, submit] = useActionState<ImportState, FormData>(
    importAccounts,
    IMPORT_IDLE,
  );

  return (
    <form action={submit} className="flex flex-col gap-4">
      <header>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          {t("title")}
        </h2>
        <p className="mt-1 text-xs text-muted">{t("hint")}</p>
      </header>

      <input
        type="file"
        name="file"
        accept=".xlsx"
        required
        className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-foreground/10 file:px-3 file:py-2 file:text-sm"
      />

      <label className="flex flex-col gap-1 text-sm">
        {t("onExisting")}
        <select
          name="on_existing"
          defaultValue="skip"
          className="rounded-md border border-border bg-transparent px-3 py-2"
        >
          <option value="skip">{t("skip")}</option>
          <option value="update">{t("update")}</option>
        </select>
      </label>

      <ImportButton label={t("submit")} pendingLabel={t("importing")} />

      {state.status === "error" && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {state.message}
        </p>
      )}

      {state.status === "success" && <ImportSummary result={state.result} />}
    </form>
  );
}

function ImportButton({
  label,
  pendingLabel,
}: {
  label: string;
  pendingLabel: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function ImportSummary({ result }: { result: ImportResult }) {
  const t = useTranslations("import");

  return (
    <div
      role="status"
      className="flex flex-col gap-3 rounded-md bg-black/5 p-3 text-sm dark:bg-white/5"
    >
      <dl className="grid grid-cols-3 gap-2 text-center">
        <Stat label={t("created")} value={result.created} />
        <Stat label={t("updated")} value={result.updated} />
        <Stat label={t("skipped")} value={result.skipped} />
      </dl>

      {result.errors.length > 0 && (
        <details open={result.errors.length <= 10}>
          <summary className="cursor-pointer text-red-700 dark:text-red-400">
            {t("rowErrors", { count: result.errors.length })}
          </summary>
          <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
            {result.errors.map((rowError) => (
              <li
                key={`${rowError.row}-${rowError.code}`}
                className="opacity-80"
              >
                <span className="font-mono">
                  {t("row", { row: rowError.row })}
                  {rowError.code ? ` · ${rowError.code}` : ""}
                </span>
                {" — "}
                {rowError.message}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

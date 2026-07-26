"use client";

import { Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IMPORT_IDLE, type ImportState } from "@/actions/state";
import { importAccounts } from "@/actions/accounts";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
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
        <h2 className="text-sm font-semibold tracking-tight">{t("title")}</h2>
        <p className="mt-1 text-xs leading-snug text-muted-foreground">
          {t("hint")}
        </p>
      </header>

      <input
        type="file"
        name="file"
        accept=".xlsx"
        required
        className="w-full cursor-pointer rounded-lg border border-dashed border-input bg-muted/40 p-3 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-foreground/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground"
      />

      <div className="flex flex-col gap-1.5">
        <Label>{t("onExisting")}</Label>
        <SearchableSelect
          name="on_existing"
          defaultValue="skip"
          options={[
            { value: "skip", label: t("skip") },
            { value: "update", label: t("update") },
          ]}
        />
      </div>

      <ImportButton label={t("submit")} pendingLabel={t("importing")} />

      {state.status === "error" && (
        <p
          role="alert"
          className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive ring-1 ring-destructive/20"
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
    <Button type="submit" disabled={pending}>
      <Upload />
      {pending ? pendingLabel : label}
    </Button>
  );
}

function ImportSummary({ result }: { result: ImportResult }) {
  const t = useTranslations("import");

  return (
    <div
      role="status"
      className="flex flex-col gap-3 rounded-xl bg-muted/60 p-3 text-sm ring-1 ring-border"
    >
      <dl className="grid grid-cols-3 gap-2 text-center">
        <Stat label={t("created")} value={result.created} />
        <Stat label={t("updated")} value={result.updated} />
        <Stat label={t("skipped")} value={result.skipped} />
      </dl>

      {result.errors.length > 0 && (
        <details open={result.errors.length <= 10}>
          <summary className="cursor-pointer text-destructive">
            {t("rowErrors", { count: result.errors.length })}
          </summary>
          <ul className="scrollbar-slim mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
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
    <div className="rounded-lg bg-card px-2 py-2 ring-1 ring-border">
      <dt className="text-[0.7rem] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

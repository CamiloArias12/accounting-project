"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import {
  changeAccountState,
  createAccount,
  updateAccount,
} from "@/actions/accounts";
import { NATURES, type Account } from "@/types/account";

interface Props {
  /**
   * Account being edited; when absent the form creates a new one.
   *
   * The parent remounts this component with `key` when the selection changes,
   * so plain `defaultValue`s are enough — no effect syncing state to props.
   */
  account: Account | null;
  onCancel: () => void;
}

export function AccountForm({ account, onCancel }: Props) {
  const t = useTranslations("form");
  const tLevel = useTranslations("level");
  const tNature = useTranslations("nature");

  const isEditing = account !== null;
  const isDeleted = account?.deleted_at != null;

  const [state, submit] = useActionState<FormState, FormData>(
    isEditing ? updateAccount : createAccount,
    IDLE,
  );
  const [lifecycleState, submitLifecycle] = useActionState<FormState, FormData>(
    changeAccountState,
    IDLE,
  );

  return (
    <div className="flex flex-col gap-4">
      <form action={submit} className="flex flex-col gap-4">
        <header className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {isEditing
              ? t("editTitle", { code: account.code })
              : t("createTitle")}
          </h2>
          {isEditing && (
            <span className="text-xs text-muted-foreground">{tLevel(account.level)}</span>
          )}
        </header>

        {isDeleted && (
          <p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400">
            {t("deletedNotice")}
          </p>
        )}

        <label className="flex flex-col gap-1 text-sm">
          {t("code")}
          <input
            name="code"
            defaultValue={account?.code ?? ""}
            readOnly={isEditing}
            required
            inputMode="numeric"
            placeholder={t("codePlaceholder")}
            className="rounded-md border border-border bg-transparent px-3 py-2 font-mono read-only:opacity-50"
          />
          {!isEditing && (
            <span className="text-xs text-muted-foreground">{t("codeHint")}</span>
          )}
        </label>

        <label className="flex flex-col gap-1 text-sm">
          {t("name")}
          <input
            name="name"
            defaultValue={account?.name ?? ""}
            required
            placeholder={t("namePlaceholder")}
            className="rounded-md border border-border bg-transparent px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          {t("nature")}
          <select
            name="nature"
            defaultValue={account?.nature ?? "Debito"}
            className="rounded-md border border-border bg-transparent px-3 py-2"
          >
            {NATURES.map((value) => (
              <option key={value} value={value}>
                {tNature(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="is_active"
            defaultChecked={account?.is_active ?? true}
          />
          {t("active")}
        </label>

        <Feedback state={state} />

        <div className="flex flex-wrap gap-2">
          <SubmitButton label={t("save")} pendingLabel={t("saving")} />
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-4 py-2 text-sm"
          >
            {t("cancel")}
          </button>
        </div>
      </form>

      {isEditing && (
        <form
          action={submitLifecycle}
          className="flex flex-col gap-2 border-t border-border pt-4"
        >
          <input type="hidden" name="code" value={account.code} />
          <input
            type="hidden"
            name="intent"
            value={isDeleted ? "restore" : "delete"}
          />
          <Feedback state={lifecycleState} />
          {isDeleted ? (
            <RestoreButton label={t("restore")} pendingLabel={t("restoring")} />
          ) : (
            <DeleteButton label={t("delete")} pendingLabel={t("deleting")} />
          )}
        </form>
      )}
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

interface ButtonProps {
  label: string;
  pendingLabel: string;
}

function SubmitButton({ label, pendingLabel }: ButtonProps) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function DeleteButton({ label, pendingLabel }: ButtonProps) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="self-start rounded-md px-4 py-2 text-sm text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function RestoreButton({ label, pendingLabel }: ButtonProps) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="self-start rounded-md border border-border px-4 py-2 text-sm disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

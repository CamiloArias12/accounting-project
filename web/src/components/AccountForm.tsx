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
import { SearchableSelect } from "@/components/SearchableSelect";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NATURES, type Account } from "@/types/account";

interface Props {
  // Account being edited; when absent the form creates a new one.
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
        <header className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">
            {isEditing
              ? t("editTitle", { code: account.code })
              : t("createTitle")}
          </h2>
          {isEditing && (
            <Badge variant="secondary">{tLevel(account.level)}</Badge>
          )}
        </header>

        {isDeleted && (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive ring-1 ring-destructive/20">
            {t("deletedNotice")}
          </p>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="account-code">{t("code")}</Label>
          <Input
            id="account-code"
            name="code"
            defaultValue={account?.code ?? ""}
            readOnly={isEditing}
            required
            inputMode="numeric"
            placeholder={t("codePlaceholder")}
            className="font-mono read-only:bg-muted/60 read-only:text-muted-foreground"
          />
          {!isEditing && (
            <span className="text-xs leading-snug text-muted-foreground">
              {t("codeHint")}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="account-name">{t("name")}</Label>
          <Input
            id="account-name"
            name="name"
            defaultValue={account?.name ?? ""}
            required
            placeholder={t("namePlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>{t("nature")}</Label>
          <SearchableSelect
            name="nature"
            defaultValue={account?.nature ?? "Debito"}
            options={NATURES.map((value) => ({
              value,
              label: tNature(value),
            }))}
          />
        </div>

        <Label className="flex items-center gap-2 font-normal">
          <input
            type="checkbox"
            name="is_active"
            defaultChecked={account?.is_active ?? true}
            className="size-4 rounded accent-primary"
          />
          {t("active")}
        </Label>

        <Feedback state={state} />

        <div className="flex flex-wrap gap-2">
          <SubmitButton label={t("save")} pendingLabel={t("saving")} />
          <Button type="button" variant="outline" onClick={onCancel}>
            {t("cancel")}
          </Button>
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
          <LifecycleButton
            deleted={isDeleted}
            label={isDeleted ? t("restore") : t("delete")}
            pendingLabel={isDeleted ? t("restoring") : t("deleting")}
          />
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
      className={`rounded-lg px-3 py-2 text-sm ring-1 ${
        isError
          ? "bg-destructive/10 text-destructive ring-destructive/20"
          : "bg-success/10 text-success ring-success/20"
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
    <Button type="submit" disabled={pending}>
      {pending ? pendingLabel : label}
    </Button>
  );
}

function LifecycleButton({
  deleted,
  label,
  pendingLabel,
}: ButtonProps & { deleted: boolean }) {
  const { pending } = useFormStatus();
  return (
    <Button
      type="submit"
      variant={deleted ? "outline" : "destructive"}
      disabled={pending}
      className="self-start"
    >
      {pending ? pendingLabel : label}
    </Button>
  );
}

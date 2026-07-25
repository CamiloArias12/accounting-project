"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/app/accounts/action-state";
import { logIn } from "@/app/login/actions";

export function LoginForm() {
  const t = useTranslations("login");
  const [state, submit] = useActionState<FormState, FormData>(logIn, IDLE);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        action={submit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-border bg-surface p-6"
      >
        <header>
          <h1 className="text-lg font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted">{t("subtitle")}</p>
        </header>

        <label className="flex flex-col gap-1 text-sm">
          {t("email")}
          <input
            name="email"
            type="email"
            autoComplete="username"
            required
            className="rounded-md border border-border bg-transparent px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          {t("password")}
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="rounded-md border border-border bg-transparent px-3 py-2"
          />
        </label>

        {state.status === "error" && (
          <p
            role="alert"
            className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
          >
            {state.message}
          </p>
        )}

        <SubmitButton />
      </form>
    </main>
  );
}

function SubmitButton() {
  const t = useTranslations("login");
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-50"
    >
      {pending ? t("signingIn") : t("signIn")}
    </button>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import { logIn } from "@/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm() {
  const t = useTranslations("login");
  const tNav = useTranslations("nav");
  const [state, submit] = useActionState<FormState, FormData>(logIn, IDLE);

  return (
    <main className="flex min-h-screen items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <span
            aria-hidden
            className="grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-primary to-indigo-500 text-base font-bold text-primary-foreground shadow-md"
          >
            AP
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              {tNav("brand")}
            </h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>
        </div>

        <form
          action={submit}
          className="flex flex-col gap-4 rounded-2xl bg-card p-6 shadow-lg ring-1 ring-border"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="login-email">{t("email")}</Label>
            <Input
              id="login-email"
              name="email"
              type="email"
              autoComplete="username"
              placeholder={t("emailPlaceholder")}
              required
              className="h-9"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="login-password">{t("password")}</Label>
            <Input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              required
              className="h-9"
            />
          </div>

          {state.status === "error" && (
            <p
              role="alert"
              className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive ring-1 ring-destructive/20"
            >
              {state.message}
            </p>
          )}

          <SubmitButton />
        </form>
      </div>
    </main>
  );
}

function SubmitButton() {
  const t = useTranslations("login");
  const { pending } = useFormStatus();

  return (
    <Button type="submit" size="lg" disabled={pending} className="mt-1 w-full">
      {pending ? t("signingIn") : t("signIn")}
    </Button>
  );
}

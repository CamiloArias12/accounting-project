"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useFormStatus } from "react-dom";

import { logOut } from "@/actions/auth";

interface Props {
  /** Null when nobody is signed in; reads stay public either way. */
  email: string | null;
}

export function SessionPanel({ email }: Props) {
  const t = useTranslations("session");

  if (!email) {
    return (
      <Link
        href="/login"
        className="rounded-md bg-primary px-3 py-1.5 text-center text-xs font-medium text-primary-foreground"
      >
        {t("signIn")}
      </Link>
    );
  }

  return (
    <form action={logOut} className="flex flex-col gap-1">
      <span className="truncate text-xs text-muted-foreground" title={email}>
        {email}
      </span>
      <SignOutButton />
    </form>
  );
}

function SignOutButton() {
  const t = useTranslations("session");
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-50"
    >
      {pending ? t("signingOut") : t("signOut")}
    </button>
  );
}

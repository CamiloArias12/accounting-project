"use client";

import { LogOut } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useFormStatus } from "react-dom";

import { logOut } from "@/actions/auth";
import { Button } from "@/components/ui/button";

interface Props {
  // Null when nobody is signed in; reads stay public either way.
  email: string | null;
}

export function SessionPanel({ email }: Props) {
  const t = useTranslations("session");

  if (!email) {
    return (
      <Button
        className="w-full"
        size="sm"
        nativeButton={false}
        render={<Link href="/login" />}
      >
        {t("signIn")}
      </Button>
    );
  }

  return (
    <form action={logOut} className="flex items-center gap-2">
      <span
        aria-hidden
        className="grid size-8 shrink-0 place-items-center rounded-full bg-primary/10 text-xs font-semibold uppercase text-primary ring-1 ring-primary/15"
      >
        {email.slice(0, 2)}
      </span>
      <span
        className="min-w-0 flex-1 truncate text-xs text-muted-foreground"
        title={email}
      >
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
    <Button
      type="submit"
      variant="ghost"
      size="icon-sm"
      disabled={pending}
      title={t("signOut")}
    >
      <LogOut />
      <span className="sr-only">{pending ? t("signingOut") : t("signOut")}</span>
    </Button>
  );
}

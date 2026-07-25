import { getTranslations } from "next-intl/server";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/LoginForm";
import { readToken } from "@/lib/session";

export async function generateMetadata() {
  const t = await getTranslations("login");
  return { title: `${t("title")} · Accounting Project` };
}

export default async function LoginPage() {
  // Already signed in: nothing to do here.
  if (await readToken()) redirect("/accounts");

  return <LoginForm />;
}

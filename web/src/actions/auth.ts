"use server";

import { redirect } from "next/navigation";

import type { FormState } from "@/actions/state";
import { ApiError, authApi } from "@/lib/api";
import { endSession, startSession } from "@/lib/session";
import { getTranslations } from "next-intl/server";

/** Must not outlive the API token, or the UI would look logged in and 401. */
const SESSION_MAX_AGE = 60 * 60;

export async function logIn(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const email = readText(formData, "email");
  const password = readText(formData, "password");

  if (!email || !password) {
    return { status: "error", message: t("login.missingFields") };
  }

  try {
    const session = await authApi.login({ email, password });
    await startSession(session.access_token, SESSION_MAX_AGE);
  } catch (caught) {
    return {
      status: "error",
      message:
        caught instanceof ApiError ? caught.message : t("errors.apiUnreachable"),
    };
  }

  // Outside the try: `redirect` works by throwing, and catching it here would
  // swallow the navigation.
  redirect("/accounts");
}

export async function logOut(): Promise<void> {
  await endSession();
  redirect("/login");
}

function readText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

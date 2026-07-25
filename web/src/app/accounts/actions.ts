"use server";

import { getTranslations } from "next-intl/server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { FormState, ImportState } from "@/app/accounts/action-state";
import { ApiError, accountsApi } from "@/lib/api";
import { NATURES, type Nature } from "@/types/account";

const ACCOUNTS_PATH = "/accounts";

export async function createAccount(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const fields = readAccountFields(formData);

  const invalid = validate(fields, t);
  if (invalid) return invalid;

  return run(async () => {
    await accountsApi.create({
      code: fields.code,
      name: fields.name,
      nature: fields.nature as Nature,
      is_active: fields.isActive,
    });
    return t("success.created", { code: fields.code });
  });
}

export async function updateAccount(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const fields = readAccountFields(formData);

  const invalid = validate(fields, t);
  if (invalid) return invalid;

  return run(async () => {
    await accountsApi.update(fields.code, {
      name: fields.name,
      nature: fields.nature as Nature,
      is_active: fields.isActive,
    });
    return t("success.updated", { code: fields.code });
  });
}

/**
 * Delete and restore share one action on purpose.
 *
 * They are the two directions of the same toggle, and each one flips the
 * condition that would pick between two separate `useActionState`s — so the
 * confirmation would vanish the instant it was earned. One action, one state,
 * one message.
 */
export async function changeAccountState(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const code = readText(formData, "code");
  if (!code) return failure(t("errors.missingCode"));

  const restoring = formData.get("intent") === "restore";

  const state = await run(async () => {
    if (restoring) {
      await accountsApi.restore(code);
      return t("success.restored", { code });
    }
    await accountsApi.remove(code);
    return t("success.deleted", { code });
  });

  // A deleted account leaves the default tree, which would unmount the form
  // mid-flight. Switching to the deleted view keeps it on screen, now offering
  // Restore. Doing it here avoids racing a client effect against the
  // revalidation; `redirect` throws by design, so it stays outside try/catch.
  if (!restoring && state.status === "success") {
    redirect(`${ACCOUNTS_PATH}?deleted=1`);
  }

  return state;
}

export async function importAccounts(
  _previous: ImportState,
  formData: FormData,
): Promise<ImportState> {
  const t = await getTranslations();
  const file = formData.get("file");

  if (!(file instanceof File) || file.size === 0) {
    return { status: "error", message: t("errors.chooseFile") };
  }

  const onExisting =
    formData.get("on_existing") === "update" ? "update" : "skip";

  try {
    const result = await accountsApi.import(file, onExisting);
    revalidatePath(ACCOUNTS_PATH);
    return { status: "success", result };
  } catch (caught) {
    return { status: "error", message: describe(caught, t) };
  }
}

type Translator = Awaited<ReturnType<typeof getTranslations>>;

interface AccountFields {
  code: string;
  name: string;
  nature: string | null;
  isActive: boolean;
}

function readAccountFields(formData: FormData): AccountFields {
  const nature = formData.get("nature");

  return {
    code: readText(formData, "code"),
    name: readText(formData, "name"),
    nature: NATURES.includes(nature as Nature) ? (nature as Nature) : null,
    isActive: formData.get("is_active") === "on",
  };
}

function validate(fields: AccountFields, t: Translator): FormState | null {
  if (!fields.code) return failure(t("errors.codeRequired"));
  if (!fields.name) return failure(t("errors.nameRequired"));
  if (!fields.nature) return failure(t("errors.invalidNature"));
  return null;
}

/** Runs the mutation, revalidates the page and turns failures into messages. */
async function run(mutation: () => Promise<string>): Promise<FormState> {
  const t = await getTranslations();

  try {
    const message = await mutation();
    revalidatePath(ACCOUNTS_PATH);
    return { status: "success", message };
  } catch (caught) {
    return failure(describe(caught, t));
  }
}

function failure(message: string): FormState {
  return { status: "error", message };
}

/**
 * Business errors carry the backend's own message, which is already specific
 * (missing parent, has children…). Only the transport failure is localized.
 */
function describe(caught: unknown, t: Translator): string {
  if (caught instanceof ApiError) return caught.message;
  return t("errors.apiUnreachable");
}

function readText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

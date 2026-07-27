"use server";

import { getTranslations } from "next-intl/server";
import { revalidatePath } from "next/cache";

import type { FormState } from "@/actions/state";
import { ApiError, exogenaApi, uvtApi } from "@/lib/api";

const PATH = "/exogena";

export async function generateExogena(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();

  const year = readNumber(formData, "year");
  if (year === null) return failure(t("exogenaErrors.yearRequired"));

  // Blank means no threshold.
  const threshold = readText(formData, "threshold_uvt") || "0";

  return run(async () => {
    const generation = await exogenaApi.generate({
      year,
      threshold_uvt: threshold,
    });
    return t("exogenaSuccess.generated", {
      records: generation.record_count,
      excluded: generation.excluded_count,
    });
  });
}

export async function refreshUvt(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();

  const year = readNumber(formData, "year");
  if (year === null) return failure(t("exogenaErrors.yearRequired"));

  return run(async () => {
    await uvtApi.refresh(year);
    return t("exogenaSuccess.refreshQueued", { year });
  });
}

export async function setUvt(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();

  const year = readNumber(formData, "year");
  const value = readText(formData, "value");
  if (year === null) return failure(t("exogenaErrors.yearRequired"));
  if (!value) return failure(t("exogenaErrors.valueRequired"));

  return run(async () => {
    await uvtApi.set(year, value);
    return t("exogenaSuccess.uvtSet", { year });
  });
}


type Translator = Awaited<ReturnType<typeof getTranslations>>;

async function run(mutation: () => Promise<string>): Promise<FormState> {
  const t = await getTranslations();

  try {
    const message = await mutation();
    revalidatePath(PATH);
    return { status: "success", message };
  } catch (caught) {
    return failure(describe(caught, t));
  }
}

function failure(message: string): FormState {
  return { status: "error", message };
}

function describe(caught: unknown, t: Translator): string {
  if (caught instanceof ApiError) return caught.message;
  return t("errors.apiUnreachable");
}

function readText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function readNumber(formData: FormData, key: string): number | null {
  const value = readText(formData, key);
  if (!value) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

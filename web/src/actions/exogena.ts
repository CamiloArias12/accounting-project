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

  // Blank means no threshold. Left as a string all the way to the API: a
  // Number round-trip on money is how a hundredth goes missing.
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
    // Accepted, not done: the fetch runs after the response, and the outcome
    // shows up in the run log. Saying "updated" here would be a lie whenever
    // the source is down.
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

// --- plumbing ---------------------------------------------------------------

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

/**
 * The backend's own message is already specific — which year has no UVT, which
 * check digit the NIT should carry. Only the transport failure is localized.
 */
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

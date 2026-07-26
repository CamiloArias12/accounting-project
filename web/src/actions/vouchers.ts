"use server";

import { getTranslations } from "next-intl/server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { FormState } from "@/actions/state";
import { ApiError, periodsApi, vouchersApi } from "@/lib/api";
import type { VoucherLineInput } from "@/types/voucher";

const PATH = "/vouchers";
const PERIODS_PATH = "/periods";

export async function saveVoucher(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const id = readNumber(formData, "id");

  const date = readText(formData, "date");
  const description = readText(formData, "description");
  if (!date) return failure(t("voucherErrors.dateRequired"));
  if (!description) return failure(t("voucherErrors.descriptionRequired"));

  const lines = readLines(formData);
  if (lines === null) return failure(t("voucherErrors.linesUnreadable"));
  if (lines.length < 2) return failure(t("voucherErrors.twoLines"));

  const payload = {
    date,
    description,
    period_year: readNumber(formData, "period_year"),
    period_month: readNumber(formData, "period_month"),
    lines,
  };

  let created: number | null = null;

  const state = await run(async () => {
    if (id === null) {
      const draft = await vouchersApi.create(payload);
      created = draft.id;
      return t("voucherSuccess.created");
    }
    await vouchersApi.update(id, payload);
    return t("voucherSuccess.updated", { id });
  });

  // A new draft has its own page from here on; an edit stays where it is.
  // `redirect` throws by design, so it lives outside the try/catch in `run`.
  if (created !== null) redirect(`${PATH}/${created}`);

  return state;
}

/**
 * Posting and reversing share one action.
 *
 * Both turn a voucher into something the books stand on, both are refused for
 * the same handful of reasons, and both leave the caller on the same screen —
 * so one state and one message is all it takes.
 */
export async function postOrReverseVoucher(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const id = readNumber(formData, "id");
  if (id === null) return failure(t("voucherErrors.missingId"));

  const reversing = formData.get("intent") === "reverse";
  let reversalId: number | null = null;

  const state = await run(async () => {
    if (!reversing) {
      const posted = await vouchersApi.post(id);
      return t("voucherSuccess.posted", { number: posted.number ?? "" });
    }

    const reversal = await vouchersApi.reverse(id, {
      date: readText(formData, "date") || null,
      // Localized here rather than left to the server default: the description
      // is data the user will read back, not a label.
      description: readText(formData, "description") || null,
    });
    reversalId = reversal.id;
    return t("voucherSuccess.reversed", { number: reversal.number ?? "" });
  });

  // The reversal is a new voucher, and it is the one worth looking at: it is
  // what now stands in the books.
  if (reversalId !== null) redirect(`${PATH}/${reversalId}`);

  return state;
}

export async function discardVoucher(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const id = readNumber(formData, "id");
  if (id === null) return failure(t("voucherErrors.missingId"));

  const state = await run(async () => {
    await vouchersApi.remove(id);
    return t("voucherSuccess.discarded");
  });

  if (state.status === "success") redirect(PATH);
  return state;
}

export async function changePeriodState(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const year = readNumber(formData, "year");
  const month = readNumber(formData, "month");
  if (year === null || month === null) {
    return failure(t("voucherErrors.missingPeriod"));
  }

  const reopening = formData.get("intent") === "reopen";
  const label = `${year}-${String(month).padStart(2, "0")}`;

  const t2 = await getTranslations();
  try {
    if (reopening) await periodsApi.reopen(year, month);
    else await periodsApi.close(year, month);

    revalidatePath(PERIODS_PATH);
    revalidatePath(PATH);
    return {
      status: "success",
      message: reopening
        ? t2("periodSuccess.reopened", { period: label })
        : t2("periodSuccess.closed", { period: label }),
    };
  } catch (caught) {
    return failure(describe(caught, t2));
  }
}

// --- plumbing ---------------------------------------------------------------

/**
 * The lines travel as JSON in a hidden field.
 *
 * They are already client state — the editor has to add and remove rows and
 * keep the two totals in step as you type — so encoding them as indexed form
 * fields would mean writing and parsing that shape twice for nothing.
 */
function readLines(formData: FormData): VoucherLineInput[] | null {
  const raw = formData.get("lines");
  if (typeof raw !== "string") return null;

  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;

    return parsed.map((line) => {
      const entry = line as Record<string, unknown>;
      return {
        account_code: String(entry.account_code ?? "").trim(),
        third_party_id:
          typeof entry.third_party_id === "number" ? entry.third_party_id : null,
        debit: String(entry.debit ?? "0"),
        credit: String(entry.credit ?? "0"),
        description: String(entry.description ?? "").trim() || null,
      };
    });
  } catch {
    return null;
  }
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

/**
 * Business errors carry the backend's own message, which is already specific:
 * how much the entry is off by, which period is closed, which account is a
 * heading. Only the transport failure is localized.
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

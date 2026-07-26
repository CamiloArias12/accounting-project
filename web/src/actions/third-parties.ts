"use server";

import { getTranslations } from "next-intl/server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { FormState } from "@/actions/state";
import { ApiError, thirdPartiesApi } from "@/lib/api";
import {
  COMPANY_TYPES,
  DOCUMENT_TYPES,
  EDUCATION_LEVELS,
  GENDERS,
  HOUSING_TYPES,
  MARITAL_STATUSES,
  TAX_REGIMES,
  type CompanyType,
  type DocumentType,
  type EducationLevel,
  type Gender,
  type HousingType,
  type LegalEntityCreate,
  type MaritalStatus,
  type NaturalPersonCreate,
  type TaxRegime,
} from "@/types/third-party";

const PATH = "/third-parties";

export async function createThirdParty(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();

  try {
    const payload = buildCreate(formData);
    return await run(async () => {
      const created = await thirdPartiesApi.create(payload);
      return t("thirdPartySuccess.created", { name: created.full_name });
    });
  } catch (caught) {
    // Thrown by the builders below when a required field is missing; the API's
    // own errors are handled inside `run`.
    return failure(describe(caught, t));
  }
}

export async function updateThirdParty(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const id = readNumber(formData, "id");
  if (id === null) return failure(t("thirdPartyErrors.missingId"));

  try {
    // Everything editable is sent, so clearing a field actually clears it.
    // `person_type` is not among them: a person does not become a company.
    const payload = buildFields(formData);

    return await run(async () => {
      const updated = await thirdPartiesApi.update(id, payload);
      return t("thirdPartySuccess.updated", { name: updated.full_name });
    });
  } catch (caught) {
    return failure(describe(caught, t));
  }
}

/**
 * Delete and restore share one action, for the same reason the accounts ones
 * do: they are two directions of the same toggle, and separate states would
 * discard the confirmation the moment it was earned.
 */
export async function changeThirdPartyState(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const t = await getTranslations();
  const id = readNumber(formData, "id");
  if (id === null) return failure(t("thirdPartyErrors.missingId"));

  const restoring = formData.get("intent") === "restore";

  const state = await run(async () => {
    const changed = restoring
      ? await thirdPartiesApi.restore(id)
      : await thirdPartiesApi.remove(id);

    return restoring
      ? t("thirdPartySuccess.restored", { name: changed.full_name })
      : t("thirdPartySuccess.deleted", { name: changed.full_name });
  });

  // A deleted third party leaves the default list, which would unmount the form
  // mid-flight. Switching to the deleted view keeps it on screen, now offering
  // Restore. `redirect` throws by design, so it stays outside try/catch.
  if (!restoring && state.status === "success") {
    redirect(`${PATH}?deleted=1&selected=${id}`);
  }

  return state;
}

// --- payload building -------------------------------------------------------

class MissingField extends Error {}

function buildCreate(
  formData: FormData,
): NaturalPersonCreate | LegalEntityCreate {
  const fields = buildFields(formData);

  return isLegal(formData)
    ? { person_type: "Legal entity", ...(fields as LegalFields) }
    : { person_type: "Natural person", ...(fields as NaturalFields) };
}

function isLegal(formData: FormData): boolean {
  return formData.get("person_type") === "Legal entity";
}

type NaturalFields = Omit<NaturalPersonCreate, "person_type">;
type LegalFields = Omit<LegalEntityCreate, "person_type">;

/**
 * Every field except `person_type`, which is what an update may change.
 * Creation adds the discriminator on top.
 */
function buildFields(formData: FormData): NaturalFields | LegalFields {
  const contact = {
    address: required(formData, "address"),
    country_id: requiredNumber(formData, "country_id"),
    department_id: readNumber(formData, "department_id"),
    city_id: readNumber(formData, "city_id"),
    mobile_phone: required(formData, "mobile_phone"),
    landline: optional(formData, "landline"),
    email: required(formData, "email"),
    tax_regime: pick(formData, "tax_regime", TAX_REGIMES) as TaxRegime,
    trade_name: optional(formData, "trade_name"),
    foreign_operations: checked(formData, "foreign_operations"),
    public_resources: checked(formData, "public_resources"),
    public_recognition: checked(formData, "public_recognition"),
    public_power: checked(formData, "public_power"),
    is_active: checked(formData, "is_active"),
  };

  if (isLegal(formData)) {
    return {
      ...contact,
      document_number: required(formData, "document_number"),
      check_digit: readNumber(formData, "check_digit"),
      legal_name: required(formData, "legal_name"),
      company_type: pick(
        formData,
        "company_type",
        COMPANY_TYPES,
      ) as CompanyType,
      company_nature: required(formData, "company_nature"),
      legal_rep_document_type: pick(
        formData,
        "legal_rep_document_type",
        DOCUMENT_TYPES,
      ) as DocumentType,
      legal_rep_document_number: required(
        formData,
        "legal_rep_document_number",
      ),
      legal_rep_name: required(formData, "legal_rep_name"),
    };
  }

  return {
    ...contact,
    document_type: pick(
      formData,
      "document_type",
      DOCUMENT_TYPES,
    ) as DocumentType,
    document_number: required(formData, "document_number"),
    check_digit: readNumber(formData, "check_digit"),
    first_name: required(formData, "first_name"),
    middle_name: optional(formData, "middle_name"),
    first_surname: required(formData, "first_surname"),
    second_surname: optional(formData, "second_surname"),
    issue_date: required(formData, "issue_date"),
    issue_city_id: requiredNumber(formData, "issue_city_id"),
    birth_date: required(formData, "birth_date"),
    birth_country_id: requiredNumber(formData, "birth_country_id"),
    birth_department_id: readNumber(formData, "birth_department_id"),
    birth_city_id: readNumber(formData, "birth_city_id"),
    gender: pick(formData, "gender", GENDERS) as Gender,
    marital_status: pick(
      formData,
      "marital_status",
      MARITAL_STATUSES,
    ) as MaritalStatus,
    housing_type: pick(formData, "housing_type", HOUSING_TYPES) as HousingType,
    education_level: pick(
      formData,
      "education_level",
      EDUCATION_LEVELS,
    ) as EducationLevel,
    profession: required(formData, "profession"),
  };
}

function readText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function required(formData: FormData, key: string): string {
  const value = readText(formData, key);
  if (!value) throw new MissingField(key);
  return value;
}

function optional(formData: FormData, key: string): string | null {
  return readText(formData, key) || null;
}

function readNumber(formData: FormData, key: string): number | null {
  const value = readText(formData, key);
  if (!value) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function requiredNumber(formData: FormData, key: string): number {
  const value = readNumber(formData, key);
  if (value === null) throw new MissingField(key);
  return value;
}

function checked(formData: FormData, key: string): boolean {
  return formData.get(key) === "on";
}

/** Rejects anything outside the closed list, so a tampered select cannot pass. */
function pick(
  formData: FormData,
  key: string,
  allowed: readonly string[],
): string {
  const value = readText(formData, key);
  if (!allowed.includes(value)) throw new MissingField(key);
  return value;
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
 * Business errors carry the backend's own message, which is already specific
 * (wrong check digit, city outside its department…). Only a missing field and
 * an unreachable API are localized here.
 */
function describe(caught: unknown, t: Translator): string {
  if (caught instanceof MissingField) {
    return t("thirdPartyErrors.missingField", { field: caught.message });
  }
  if (caught instanceof ApiError) return caught.message;
  return t("errors.apiUnreachable");
}

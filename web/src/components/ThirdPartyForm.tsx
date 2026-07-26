"use client";

import { useTranslations } from "next-intl";
import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";

import { IDLE, type FormState } from "@/actions/state";
import {
  changeThirdPartyState,
  createThirdParty,
  updateThirdParty,
} from "@/actions/third-parties";
import { IssueCityField } from "@/components/IssueCityField";
import { PlaceFields } from "@/components/PlaceFields";
import {
  COMPANY_TYPES,
  DOCUMENT_TYPES,
  DOCUMENT_WITH_CHECK_DIGIT,
  EDUCATION_LEVELS,
  GENDERS,
  HOUSING_TYPES,
  MARITAL_STATUSES,
  TAX_REGIMES,
  type City,
  type Country,
  type Department,
  type DocumentType,
  type PersonType,
  type ThirdParty,
} from "@/types/third-party";

/** Lists resolved on the server, so an edit form shows its selection at once. */
export interface Preloaded {
  addressDepartments: Department[];
  addressCities: City[];
  birthDepartments: Department[];
  birthCities: City[];
  issueCity: City | null;
  issueCities: City[];
}

interface Props {
  /**
   * The third party being edited; absent when registering a new one.
   *
   * The parent remounts this with `key` when the selection changes, so plain
   * `defaultValue`s are enough — no effect syncing state to props.
   */
  thirdParty: ThirdParty | null;
  countries: Country[];
  /** Colombian departments, for the issue-city cascade. */
  departments: Department[];
  preloaded: Preloaded;
  onCancel: () => void;
}

export function ThirdPartyForm({
  thirdParty,
  countries,
  departments,
  preloaded,
  onCancel,
}: Props) {
  const t = useTranslations("thirdPartyForm");

  const isEditing = thirdParty !== null;
  const isDeleted = thirdParty?.deleted_at != null;

  const [personType, setPersonType] = useState<PersonType>(
    thirdParty?.person_type ?? "Natural person",
  );
  const [documentType, setDocumentType] = useState<DocumentType>(
    thirdParty?.document_type ?? "Citizen ID",
  );

  const isLegal = personType === "Legal entity";
  // A legal entity is always a NIT, so its check digit is always in play.
  const hasCheckDigit = isLegal || documentType === DOCUMENT_WITH_CHECK_DIGIT;

  const [state, submit] = useActionState<FormState, FormData>(
    isEditing ? updateThirdParty : createThirdParty,
    IDLE,
  );
  const [lifecycleState, submitLifecycle] = useActionState<FormState, FormData>(
    changeThirdPartyState,
    IDLE,
  );

  return (
    <div className="flex flex-col gap-4">
      <form action={submit} className="flex flex-col gap-5">
        {isEditing && <input type="hidden" name="id" value={thirdParty.id} />}
        <input type="hidden" name="person_type" value={personType} />

        <header className="flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            {isEditing ? t("editTitle") : t("createTitle")}
          </h2>
          {isEditing && (
            <span className="font-mono text-xs text-muted">
              {thirdParty.formatted_document}
            </span>
          )}
        </header>

        {isDeleted && (
          <p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400">
            {t("deletedNotice")}
          </p>
        )}

        {/* A person does not become a company: the choice is made once. */}
        {!isEditing && (
          <fieldset className="flex flex-wrap gap-4 text-sm">
            <legend className="mb-1 text-xs uppercase tracking-wide text-muted">
              {t("personType")}
            </legend>
            {(["Natural person", "Legal entity"] as const).map((value) => (
              <label key={value} className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={personType === value}
                  onChange={() => setPersonType(value)}
                />
                {t(`personTypes.${value}`)}
              </label>
            ))}
          </fieldset>
        )}

        <Section title={t("identification")}>
          {/* Uneven columns: a document type label is long ("Cédula de
              ciudadanía"), a check digit is one character. */}
          <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr_0.5fr]">
            {isLegal ? (
              <p className="flex flex-col gap-1 text-sm">
                {t("documentType")}
                <span className="rounded-md border border-border px-3 py-2 text-muted">
                  NIT
                </span>
              </p>
            ) : (
              <label className="flex flex-col gap-1 text-sm">
                {t("documentType")}
                <select
                  name="document_type"
                  value={documentType}
                  onChange={(event) =>
                    setDocumentType(event.target.value as DocumentType)
                  }
                  className="rounded-md border border-border bg-transparent px-3 py-2"
                >
                  {DOCUMENT_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {t(`documentTypes.${value}`)}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="flex flex-col gap-1 text-sm">
              {t("documentNumber")}
              <input
                name="document_number"
                defaultValue={thirdParty?.document_number ?? ""}
                required
                className="rounded-md border border-border bg-transparent px-3 py-2 font-mono"
              />
            </label>

            {hasCheckDigit && (
              <label className="flex flex-col gap-1 text-sm">
                {t("checkDigit")}
                <input
                  name="check_digit"
                  type="number"
                  min={0}
                  max={9}
                  defaultValue={thirdParty?.check_digit ?? ""}
                  className="rounded-md border border-border bg-transparent px-3 py-2 font-mono"
                />
                <span className="text-xs text-muted">{t("checkDigitHint")}</span>
              </label>
            )}
          </div>
        </Section>

        {isLegal ? (
          <LegalFields thirdParty={thirdParty} />
        ) : (
          <NaturalFields
            thirdParty={thirdParty}
            countries={countries}
            departments={departments}
            preloaded={preloaded}
          />
        )}

        <Section title={t("contact")}>
          <label className="flex flex-col gap-1 text-sm">
            {t("tradeName")}
            <input
              name="trade_name"
              defaultValue={thirdParty?.trade_name ?? ""}
              className="rounded-md border border-border bg-transparent px-3 py-2"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t("address")}
            <input
              name="address"
              defaultValue={thirdParty?.address ?? ""}
              required
              className="rounded-md border border-border bg-transparent px-3 py-2"
            />
          </label>

          <PlaceFields
            countries={countries}
            names={{
              country: "country_id",
              department: "department_id",
              city: "city_id",
            }}
            initial={{
              countryId: thirdParty?.country_id ?? null,
              departmentId: thirdParty?.department_id ?? null,
              cityId: thirdParty?.city_id ?? null,
            }}
            initialDepartments={preloaded.addressDepartments}
            initialCities={preloaded.addressCities}
          />

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="flex flex-col gap-1 text-sm">
              {t("mobilePhone")}
              <input
                name="mobile_phone"
                defaultValue={thirdParty?.mobile_phone ?? ""}
                required
                className="rounded-md border border-border bg-transparent px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("landline")}
              <input
                name="landline"
                defaultValue={thirdParty?.landline ?? ""}
                className="rounded-md border border-border bg-transparent px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("email")}
              <input
                name="email"
                type="email"
                defaultValue={thirdParty?.email ?? ""}
                required
                className="rounded-md border border-border bg-transparent px-3 py-2"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1 text-sm sm:max-w-xs">
            {t("taxRegime")}
            <select
              name="tax_regime"
              defaultValue={thirdParty?.tax_regime ?? "Not VAT responsible"}
              className="rounded-md border border-border bg-transparent px-3 py-2"
            >
              {TAX_REGIMES.map((value) => (
                <option key={value} value={value}>
                  {t(`taxRegimes.${value}`)}
                </option>
              ))}
            </select>
          </label>
        </Section>

        <Section title={t("declarations")} hint={t("declarationsHint")}>
          <div className="grid gap-2 sm:grid-cols-2">
            <Check
              name="foreign_operations"
              label={t("foreignOperations")}
              defaultChecked={thirdParty?.foreign_operations ?? false}
            />
            <Check
              name="public_resources"
              label={t("publicResources")}
              defaultChecked={thirdParty?.public_resources ?? false}
            />
            <Check
              name="public_recognition"
              label={t("publicRecognition")}
              defaultChecked={thirdParty?.public_recognition ?? false}
            />
            <Check
              name="public_power"
              label={t("publicPower")}
              defaultChecked={thirdParty?.public_power ?? false}
            />
          </div>
        </Section>

        <Check
          name="is_active"
          label={t("active")}
          defaultChecked={thirdParty?.is_active ?? true}
        />

        <Feedback state={state} />

        <div className="flex flex-wrap gap-2">
          <SubmitButton label={t("save")} pendingLabel={t("saving")} />
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-4 py-2 text-sm"
          >
            {t("cancel")}
          </button>
        </div>
      </form>

      {isEditing && (
        <form
          action={submitLifecycle}
          className="flex flex-col gap-2 border-t border-border pt-4"
        >
          <input type="hidden" name="id" value={thirdParty.id} />
          <input
            type="hidden"
            name="intent"
            value={isDeleted ? "restore" : "delete"}
          />
          <Feedback state={lifecycleState} />
          <LifecycleButton
            deleted={isDeleted}
            label={isDeleted ? t("restore") : t("delete")}
            pendingLabel={isDeleted ? t("restoring") : t("deleting")}
          />
        </form>
      )}
    </div>
  );
}

interface NaturalProps {
  thirdParty: ThirdParty | null;
  countries: Country[];
  departments: Department[];
  preloaded: Preloaded;
}

function NaturalFields({
  thirdParty,
  countries,
  departments,
  preloaded,
}: NaturalProps) {
  const t = useTranslations("thirdPartyForm");

  return (
    <>
      <Section title={t("names")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Text name="first_name" label={t("firstName")} value={thirdParty?.first_name} required />
          <Text name="middle_name" label={t("middleName")} value={thirdParty?.middle_name} />
          <Text name="first_surname" label={t("firstSurname")} value={thirdParty?.first_surname} required />
          <Text name="second_surname" label={t("secondSurname")} value={thirdParty?.second_surname} />
        </div>
      </Section>

      <Section title={t("document")}>
        <label className="flex flex-col gap-1 text-sm sm:max-w-xs">
          {t("issueDate")}
          <input
            name="issue_date"
            type="date"
            defaultValue={thirdParty?.issue_date ?? ""}
            required
            className="rounded-md border border-border bg-transparent px-3 py-2"
          />
        </label>
        <IssueCityField
          departments={departments}
          initialCity={preloaded.issueCity}
          initialCities={preloaded.issueCities}
        />
      </Section>

      <Section title={t("birth")}>
        <label className="flex flex-col gap-1 text-sm sm:max-w-xs">
          {t("birthDate")}
          <input
            name="birth_date"
            type="date"
            defaultValue={thirdParty?.birth_date ?? ""}
            required
            className="rounded-md border border-border bg-transparent px-3 py-2"
          />
        </label>
        <PlaceFields
          countries={countries}
          names={{
            country: "birth_country_id",
            department: "birth_department_id",
            city: "birth_city_id",
          }}
          initial={{
            countryId: thirdParty?.birth_country_id ?? null,
            departmentId: thirdParty?.birth_department_id ?? null,
            cityId: thirdParty?.birth_city_id ?? null,
          }}
          initialDepartments={preloaded.birthDepartments}
          initialCities={preloaded.birthCities}
        />
      </Section>

      <Section title={t("personal")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Choice
            name="gender"
            label={t("gender")}
            values={GENDERS}
            prefix="genders"
            value={thirdParty?.gender}
          />
          <Choice
            name="marital_status"
            label={t("maritalStatus")}
            values={MARITAL_STATUSES}
            prefix="maritalStatuses"
            value={thirdParty?.marital_status}
          />
          <Choice
            name="housing_type"
            label={t("housingType")}
            values={HOUSING_TYPES}
            prefix="housingTypes"
            value={thirdParty?.housing_type}
          />
          <Choice
            name="education_level"
            label={t("educationLevel")}
            values={EDUCATION_LEVELS}
            prefix="educationLevels"
            value={thirdParty?.education_level}
          />
        </div>
        <Text
          name="profession"
          label={t("profession")}
          value={thirdParty?.profession}
          required
        />
      </Section>
    </>
  );
}

function LegalFields({ thirdParty }: { thirdParty: ThirdParty | null }) {
  const t = useTranslations("thirdPartyForm");

  return (
    <>
      <Section title={t("company")}>
        <Text
          name="legal_name"
          label={t("legalName")}
          value={thirdParty?.legal_name}
          required
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Choice
            name="company_type"
            label={t("companyType")}
            values={COMPANY_TYPES}
            prefix="companyTypes"
            value={thirdParty?.company_type}
          />
          <Text
            name="company_nature"
            label={t("companyNature")}
            value={thirdParty?.company_nature}
            required
          />
        </div>
      </Section>

      <Section title={t("legalRepresentative")}>
        <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr]">
          <Choice
            name="legal_rep_document_type"
            label={t("documentType")}
            values={DOCUMENT_TYPES}
            prefix="documentTypes"
            value={thirdParty?.legal_rep_document_type}
          />
          <Text
            name="legal_rep_document_number"
            label={t("documentNumber")}
            value={thirdParty?.legal_rep_document_number}
            required
          />
        </div>
        <Text
          name="legal_rep_name"
          label={t("legalRepName")}
          value={thirdParty?.legal_rep_name}
          required
        />
      </Section>
    </>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="flex flex-col gap-3 border-t border-border pt-4">
      <legend className="text-xs uppercase tracking-wide text-muted">
        {title}
      </legend>
      {hint && <p className="-mt-1 text-xs text-muted">{hint}</p>}
      {children}
    </fieldset>
  );
}

function Text({
  name,
  label,
  value,
  required = false,
}: {
  name: string;
  label: string;
  value?: string | null;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label}
      <input
        name={name}
        defaultValue={value ?? ""}
        required={required}
        className="rounded-md border border-border bg-transparent px-3 py-2"
      />
    </label>
  );
}

function Choice({
  name,
  label,
  values,
  prefix,
  value,
}: {
  name: string;
  label: string;
  values: readonly string[];
  prefix: string;
  value?: string | null;
}) {
  const t = useTranslations("thirdPartyForm");

  return (
    <label className="flex flex-col gap-1 text-sm">
      {label}
      <select
        name={name}
        defaultValue={value ?? values[0]}
        className="rounded-md border border-border bg-transparent px-3 py-2"
      >
        {values.map((option) => (
          <option key={option} value={option}>
            {t(`${prefix}.${option}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Check({
  name,
  label,
  defaultChecked,
}: {
  name: string;
  label: string;
  defaultChecked: boolean;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" name={name} defaultChecked={defaultChecked} />
      {label}
    </label>
  );
}

function Feedback({ state }: { state: FormState }) {
  if (state.status === "idle") return null;

  const isError = state.status === "error";
  return (
    <p
      role={isError ? "alert" : "status"}
      className={`rounded-md px-3 py-2 text-sm ${
        isError
          ? "bg-red-500/10 text-red-700 dark:text-red-400"
          : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      }`}
    >
      {state.message}
    </p>
  );
}

function SubmitButton({
  label,
  pendingLabel,
}: {
  label: string;
  pendingLabel: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function LifecycleButton({
  deleted,
  label,
  pendingLabel,
}: {
  deleted: boolean;
  label: string;
  pendingLabel: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className={
        deleted
          ? "self-start rounded-md border border-border px-4 py-2 text-sm disabled:opacity-50"
          : "self-start rounded-md px-4 py-2 text-sm text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"
      }
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

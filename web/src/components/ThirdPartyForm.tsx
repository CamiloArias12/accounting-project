"use client";

import { Building2, User } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActionState, useEffect, useState } from "react";
import { useFormStatus } from "react-dom";
import { toast } from "sonner";

import { IDLE, type FormState } from "@/actions/state";
import {
  changeThirdPartyState,
  createThirdParty,
  updateThirdParty,
} from "@/actions/third-parties";
import { IssueCityField } from "@/components/IssueCityField";
import { PlaceFields } from "@/components/PlaceFields";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
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

  useAnnounce(state);
  useAnnounce(lifecycleState);

  return (
    <div className="flex flex-col gap-6">
      <form action={submit} className="flex flex-col gap-7">
        {isEditing && <input type="hidden" name="id" value={thirdParty.id} />}
        <input type="hidden" name="person_type" value={personType} />

        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
              {isLegal ? (
                <Building2 className="size-5" />
              ) : (
                <User className="size-5" />
              )}
            </span>
            <div>
              <h2 className="text-lg font-semibold tracking-tight">
                {isEditing ? t("editTitle") : t("createTitle")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t(`personTypes.${personType}`)}
                {isEditing && ` · ${thirdParty.formatted_document}`}
              </p>
            </div>
          </div>
          {isDeleted && (
            <Badge variant="destructive">{t("deletedBadgeShort")}</Badge>
          )}
        </header>

        {isDeleted && (
          <p className="rounded-lg bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive ring-1 ring-destructive/20">
            {t("deletedNotice")}
          </p>
        )}

        {/* A person does not become a company: the choice is made once. */}
        {!isEditing && (
          <Section title={t("personType")}>
            <div
              role="radiogroup"
              aria-label={t("personType")}
              className="grid gap-2 sm:grid-cols-2"
            >
              {(["Natural person", "Legal entity"] as const).map((value) => {
                const active = personType === value;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setPersonType(value)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl border p-3 text-left text-sm transition-all outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                      active
                        ? "border-primary/40 bg-primary/5 text-foreground shadow-xs"
                        : "border-border bg-transparent text-muted-foreground hover:border-foreground/20 hover:bg-muted/50",
                    )}
                  >
                    <span
                      className={cn(
                        "grid size-8 shrink-0 place-items-center rounded-lg",
                        active
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {value === "Legal entity" ? (
                        <Building2 className="size-4" />
                      ) : (
                        <User className="size-4" />
                      )}
                    </span>
                    <span className="font-medium">
                      {t(`personTypes.${value}`)}
                    </span>
                  </button>
                );
              })}
            </div>
          </Section>
        )}

        <Section title={t("identification")}>
          {/* Uneven columns: a document type label is long ("Cédula de
              ciudadanía"), a check digit is one character. */}
          <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr_0.5fr]">
            <div className="flex flex-col gap-1.5">
              <Label>{t("documentType")}</Label>
              {isLegal ? (
                <div className="flex h-8 items-center rounded-lg border border-dashed border-input px-2.5 text-sm text-muted-foreground">
                  NIT
                </div>
              ) : (
                <SearchableSelect
                  name="document_type"
                  value={documentType}
                  onChange={(next) => setDocumentType(next as DocumentType)}
                  options={DOCUMENT_TYPES.map((value) => ({
                    value,
                    label: t(`documentTypes.${value}`),
                  }))}
                />
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="document_number">{t("documentNumber")}</Label>
              <Input
                id="document_number"
                name="document_number"
                defaultValue={thirdParty?.document_number ?? ""}
                required
                inputMode="numeric"
                className="font-mono"
              />
            </div>

            {hasCheckDigit && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="check_digit">{t("checkDigit")}</Label>
                <Input
                  id="check_digit"
                  name="check_digit"
                  type="number"
                  min={0}
                  max={9}
                  defaultValue={thirdParty?.check_digit ?? ""}
                  className="font-mono"
                />
                <Hint>{t("checkDigitHint")}</Hint>
              </div>
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
          <div className="grid gap-3 sm:grid-cols-2">
            <Text
              name="trade_name"
              label={t("tradeName")}
              value={thirdParty?.trade_name}
            />
            <Text
              name="address"
              label={t("address")}
              value={thirdParty?.address}
              required
            />
          </div>

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
            <Text
              name="mobile_phone"
              label={t("mobilePhone")}
              value={thirdParty?.mobile_phone}
              required
            />
            <Text
              name="landline"
              label={t("landline")}
              value={thirdParty?.landline}
            />
            <Text
              name="email"
              label={t("email")}
              type="email"
              value={thirdParty?.email}
              required
            />
          </div>

          <div className="sm:max-w-xs">
            <Choice
              name="tax_regime"
              label={t("taxRegime")}
              values={TAX_REGIMES}
              prefix="taxRegimes"
              value={thirdParty?.tax_regime ?? "Not VAT responsible"}
            />
          </div>
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

        {/* Sticky, because this form is long enough that the save button was
            a scroll away from whatever field was just filled in. */}
        <div className="sticky bottom-0 -mx-4 flex flex-wrap gap-2 border-t border-border bg-card/85 px-4 py-3 backdrop-blur-sm sm:-mx-6 sm:px-6">
          <SubmitButton label={t("save")} pendingLabel={t("saving")} />
          <Button type="button" variant="outline" onClick={onCancel}>
            {t("cancel")}
          </Button>
        </div>
      </form>

      {isEditing && (
        <form
          action={submitLifecycle}
          className="flex flex-col gap-2 border-t border-border pt-5"
        >
          <input type="hidden" name="id" value={thirdParty.id} />
          <input
            type="hidden"
            name="intent"
            value={isDeleted ? "restore" : "delete"}
          />
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
        <div className="sm:max-w-xs">
          <Text
            name="issue_date"
            label={t("issueDate")}
            type="date"
            value={thirdParty?.issue_date}
            required
          />
        </div>
        <IssueCityField
          departments={departments}
          initialCity={preloaded.issueCity}
          initialCities={preloaded.issueCities}
        />
      </Section>

      <Section title={t("birth")}>
        <div className="sm:max-w-xs">
          <Text
            name="birth_date"
            label={t("birthDate")}
            type="date"
            value={thirdParty?.birth_date}
            required
          />
        </div>
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

/**
 * One block of the form.
 *
 * The heading sits in its own column above `md`, which turns a 40-field wall
 * into a document with a margin: the eye can find "Contact" without reading
 * the fields on the way there.
 */
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
    <fieldset className="grid gap-x-8 gap-y-3 md:grid-cols-[11rem_1fr]">
      <legend className="sr-only">{title}</legend>
      <div aria-hidden className="md:pt-0.5">
        <p className="text-sm font-semibold tracking-tight">{title}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </div>
      <div className="flex min-w-0 flex-col gap-3">{children}</div>
    </fieldset>
  );
}

function Hint({ children }: { children: React.ReactNode }) {
  return <span className="text-xs text-muted-foreground">{children}</span>;
}

function Text({
  name,
  label,
  value,
  type = "text",
  required = false,
}: {
  name: string;
  label: string;
  value?: string | null;
  type?: string;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={name}>{label}</Label>
      <Input
        id={name}
        name={name}
        type={type}
        defaultValue={value ?? ""}
        required={required}
      />
    </div>
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
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      {/* A real `<select>` rides along inside SearchableSelect: the server
          action reads `FormData`, which a listbox on its own does not fill. */}
      <SearchableSelect
        name={name}
        defaultValue={value ?? values[0]}
        options={values.map((option) => ({
          value: option,
          label: t(`${prefix}.${option}`),
        }))}
      />
    </div>
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
    <Label className="flex items-start gap-2.5 rounded-lg px-2 py-1.5 font-normal transition-colors hover:bg-muted/60">
      <input
        type="checkbox"
        name={name}
        defaultChecked={defaultChecked}
        className="mt-0.5 size-4 shrink-0 rounded accent-primary"
      />
      <span className="leading-snug">{label}</span>
    </Label>
  );
}

/**
 * Surfaces an action's outcome as a toast rather than a paragraph under the
 * form, which on a form this long meant scrolling to find out what happened.
 */
function useAnnounce(state: FormState) {
  useEffect(() => {
    if (state.status === "success") toast.success(state.message);
    if (state.status === "error") toast.error(state.message);
  }, [state]);
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
    <Button type="submit" disabled={pending}>
      {pending ? pendingLabel : label}
    </Button>
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
    <Button
      type="submit"
      variant={deleted ? "outline" : "destructive"}
      disabled={pending}
      className="self-start"
    >
      {pending ? pendingLabel : label}
    </Button>
  );
}

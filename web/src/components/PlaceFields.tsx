"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCities, fetchDepartments } from "@/actions/locations";
import type { City, Country, Department } from "@/types/third-party";

export interface PlaceNames {
  country: string;
  department: string;
  city: string;
}

export interface PlaceValue {
  countryId: number | null;
  departmentId: number | null;
  cityId: number | null;
}

interface Props {
  countries: Country[];
  /** Field names, so the same component serves the address and the birthplace. */
  names: PlaceNames;
  initial: PlaceValue;
  /** Preloaded so an edit form shows its selection before any fetch resolves. */
  initialDepartments?: Department[];
  initialCities?: City[];
  requireCountry?: boolean;
}

/**
 * Country → department → city, each list narrowed by the one above it.
 *
 * Department and city stay optional on purpose: the DANE catalog only covers
 * Colombia, so a foreign address stops at the country. The API refuses a city
 * whose department does not match, which is the check this UI cannot enforce
 * on its own.
 */
export function PlaceFields({
  countries,
  names,
  initial,
  initialDepartments = [],
  initialCities = [],
  requireCountry = true,
}: Props) {
  const t = useTranslations("thirdPartyForm");

  const [countryId, setCountryId] = useState(initial.countryId ?? "");
  const [departmentId, setDepartmentId] = useState(initial.departmentId ?? "");
  const [cityId, setCityId] = useState(initial.cityId ?? "");

  const [departments, setDepartments] = useState<Department[]>(initialDepartments);
  const [cities, setCities] = useState<City[]>(initialCities);

  // Only loading happens here. Clearing is done by the handlers below, where
  // the choice that invalidated the list was made: emptying it from an effect
  // would be a second render nobody asked for.
  useEffect(() => {
    if (countryId === "") return;

    let current = true;
    fetchDepartments(Number(countryId)).then((loaded) => {
      // Ignore a response that arrived after the country changed again.
      if (current) setDepartments(loaded);
    });
    return () => {
      current = false;
    };
  }, [countryId]);

  useEffect(() => {
    if (departmentId === "") return;

    let current = true;
    fetchCities(Number(departmentId)).then((loaded) => {
      if (current) setCities(loaded);
    });
    return () => {
      current = false;
    };
  }, [departmentId]);

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <label className="flex flex-col gap-1 text-sm">
        {t("country")}
        <select
          name={names.country}
          value={countryId}
          required={requireCountry}
          onChange={(event) => {
            setCountryId(event.target.value);
            // Whatever was chosen below no longer belongs to this country.
            setDepartments([]);
            setDepartmentId("");
            setCities([]);
            setCityId("");
          }}
          className="rounded-md border border-border bg-transparent px-3 py-2"
        >
          <option value="">{t("choose")}</option>
          {countries.map((country) => (
            <option key={country.id} value={country.id}>
              {country.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        {t("department")}
        <select
          name={names.department}
          value={departmentId}
          disabled={departments.length === 0}
          onChange={(event) => {
            setDepartmentId(event.target.value);
            setCities([]);
            setCityId("");
          }}
          className="rounded-md border border-border bg-transparent px-3 py-2 disabled:opacity-50"
        >
          <option value="">{t("choose")}</option>
          {departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        {t("city")}
        <select
          name={names.city}
          value={cityId}
          disabled={cities.length === 0}
          onChange={(event) => setCityId(event.target.value)}
          className="rounded-md border border-border bg-transparent px-3 py-2 disabled:opacity-50"
        >
          <option value="">{t("choose")}</option>
          {cities.map((city) => (
            <option key={city.id} value={city.id}>
              {city.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

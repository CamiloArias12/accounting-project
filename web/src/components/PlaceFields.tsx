"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCities, fetchDepartments } from "@/actions/locations";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Label } from "@/components/ui/label";
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
  // Field names, so the same component serves the address and the birthplace.
  names: PlaceNames;
  initial: PlaceValue;
  initialDepartments?: Department[];
  initialCities?: City[];
  requireCountry?: boolean;
}

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

  useEffect(() => {
    if (countryId === "") return;

    let current = true;
    fetchDepartments(Number(countryId)).then((loaded) => {
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
      <div className="flex flex-col gap-1.5">
        <Label>{t("country")}</Label>
        <SearchableSelect
          name={names.country}
          value={String(countryId)}
          required={requireCountry}
          placeholder={t("choose")}
          searchPlaceholder={t("searchCountry")}
          options={countries.map((country) => ({
            value: String(country.id),
            label: country.name,
          }))}
          onChange={(next) => {
            setCountryId(next);
            setDepartments([]);
            setDepartmentId("");
            setCities([]);
            setCityId("");
          }}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>{t("department")}</Label>
        <SearchableSelect
          name={names.department}
          value={String(departmentId)}
          disabled={departments.length === 0}
          placeholder={t("choose")}
          searchPlaceholder={t("searchDepartment")}
          options={departments.map((department) => ({
            value: String(department.id),
            label: department.name,
          }))}
          onChange={(next) => {
            setDepartmentId(next);
            setCities([]);
            setCityId("");
          }}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>{t("city")}</Label>
        <SearchableSelect
          name={names.city}
          value={String(cityId)}
          disabled={cities.length === 0}
          placeholder={t("choose")}
          searchPlaceholder={t("searchCity")}
          options={cities.map((city) => ({
            value: String(city.id),
            label: city.name,
          }))}
          onChange={setCityId}
        />
      </div>
    </div>
  );
}

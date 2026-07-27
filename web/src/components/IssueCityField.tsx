"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCities } from "@/actions/locations";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Label } from "@/components/ui/label";
import type { City, Department } from "@/types/third-party";

interface Props {
  // Colombian departments; a document is issued inside the country.
  departments: Department[];
  initialCity: City | null;
  initialCities?: City[];
}

export function IssueCityField({
  departments,
  initialCity,
  initialCities = [],
}: Props) {
  const t = useTranslations("thirdPartyForm");

  const [departmentId, setDepartmentId] = useState<number | "">(
    initialCity?.department_id ?? "",
  );
  const [cityId, setCityId] = useState<number | "">(initialCity?.id ?? "");
  const [cities, setCities] = useState<City[]>(initialCities);

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
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="flex flex-col gap-1.5">
        <Label>{t("issueDepartment")}</Label>
        <SearchableSelect
          name="issue_department_helper"
          value={String(departmentId)}
          placeholder={t("choose")}
          searchPlaceholder={t("searchDepartment")}
          options={departments.map((department) => ({
            value: String(department.id),
            label: department.name,
          }))}
          onChange={(next) => {
            setDepartmentId(next === "" ? "" : Number(next));
            setCities([]);
            setCityId("");
          }}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>{t("issueCity")}</Label>
        <SearchableSelect
          name="issue_city_id"
          value={String(cityId)}
          required
          disabled={cities.length === 0}
          placeholder={t("choose")}
          searchPlaceholder={t("searchCity")}
          options={cities.map((city) => ({
            value: String(city.id),
            label: city.name,
          }))}
          onChange={(next) => setCityId(next === "" ? "" : Number(next))}
        />
      </div>
    </div>
  );
}

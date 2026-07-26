"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCities } from "@/actions/locations";
import { NativeSelect } from "@/components/NativeSelect";
import { Label } from "@/components/ui/label";
import type { City, Department } from "@/types/third-party";

interface Props {
  /** Colombian departments; a document is issued inside the country. */
  departments: Department[];
  initialCity: City | null;
  initialCities?: City[];
}

/**
 * The city a document was issued in.
 *
 * Narrowed by department rather than searched free-text: 1122 municipalities in
 * one dropdown is unusable, and the stored value is only the city, so an edit
 * has to resolve its department to preselect the first select.
 */
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

  // Loading only; the handler clears the list when the department changes.
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
        <NativeSelect
          name="issue_department_helper"
          value={String(departmentId)}
          placeholder={t("choose")}
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
        <NativeSelect
          name="issue_city_id"
          value={String(cityId)}
          required
          disabled={cities.length === 0}
          placeholder={t("choose")}
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

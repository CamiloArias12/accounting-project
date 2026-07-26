"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCities } from "@/actions/locations";
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
      <label className="flex flex-col gap-1 text-sm">
        {t("issueDepartment")}
        <select
          value={departmentId}
          onChange={(event) => {
            setDepartmentId(
              event.target.value === "" ? "" : Number(event.target.value),
            );
            setCities([]);
            setCityId("");
          }}
          className="rounded-md border border-border bg-transparent px-3 py-2"
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
        {t("issueCity")}
        <select
          name="issue_city_id"
          value={cityId}
          required
          disabled={cities.length === 0}
          onChange={(event) =>
            setCityId(event.target.value === "" ? "" : Number(event.target.value))
          }
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

import { notFound } from "next/navigation";

import type { Preloaded } from "@/components/ThirdPartyForm";
import { ThirdPartyPage } from "@/components/ThirdPartyPage";
import { ApiError, locationsApi, thirdPartiesApi } from "@/lib/api";
import type {
  City,
  Country,
  Department,
  ThirdParty,
} from "@/types/third-party";

export const metadata = {
  title: "Third party · Accounting Project",
};

interface Props {
  params: Promise<{ id: string }>;
}

const EMPTY: Preloaded = {
  addressDepartments: [],
  addressCities: [],
  birthDepartments: [],
  birthCities: [],
  issueCity: null,
  issueCities: [],
};

export default async function ThirdPartyDetailPage({ params }: Props) {
  const id = Number((await params).id);
  if (!Number.isInteger(id)) notFound();

  let thirdParty: ThirdParty | null = null;
  let countries: Country[] = [];
  let departments: Department[] = [];
  let preloaded = EMPTY;
  let loadError: string | null = null;

  try {
    [thirdParty, countries] = await Promise.all([
      // Deleted ones are still reachable: the page is where they get restored.
      thirdPartiesApi.get(id, true),
      locationsApi.countries(),
    ]);

    const colombia = countries.find((country) => country.iso_code === "CO");
    if (colombia) {
      departments = await locationsApi.departments({
        country_id: colombia.id,
        limit: 100,
      });
    }
    preloaded = await preload(thirdParty);
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) notFound();
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ThirdPartyPage
      thirdParty={thirdParty}
      countries={countries}
      departments={departments}
      preloaded={preloaded}
      loadError={loadError}
    />
  );
}

/**
 * The lists behind the cascades.
 *
 * Resolved here rather than fetched by the form on mount, so an edit shows its
 * departments and municipalities already selected instead of blanking them for
 * a moment. The issue city is looked up on its own because only the city is
 * stored — its department has to be read back off it.
 */
async function preload(thirdParty: ThirdParty): Promise<Preloaded> {
  const [
    addressDepartments,
    addressCities,
    birthDepartments,
    birthCities,
    issueCity,
  ] = await Promise.all([
    listDepartments(thirdParty.country_id),
    listCities(thirdParty.department_id),
    listDepartments(thirdParty.birth_country_id),
    listCities(thirdParty.birth_department_id),
    getCity(thirdParty.issue_city_id),
  ]);

  return {
    addressDepartments,
    addressCities,
    birthDepartments,
    birthCities,
    issueCity,
    issueCities: await listCities(issueCity?.department_id ?? null),
  };
}

async function listDepartments(countryId: number | null): Promise<Department[]> {
  if (countryId === null) return [];
  try {
    return await locationsApi.departments({ country_id: countryId, limit: 100 });
  } catch {
    return [];
  }
}

async function listCities(departmentId: number | null): Promise<City[]> {
  if (departmentId === null) return [];
  try {
    return await locationsApi.cities({
      department_id: departmentId,
      limit: 200,
    });
  } catch {
    return [];
  }
}

async function getCity(cityId: number | null): Promise<City | null> {
  if (cityId === null) return null;
  try {
    return await locationsApi.city(cityId);
  } catch {
    return null;
  }
}

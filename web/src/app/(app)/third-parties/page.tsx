import { ThirdPartiesWorkspace } from "@/components/ThirdPartiesWorkspace";
import type { Preloaded } from "@/components/ThirdPartyForm";
import { ApiError, locationsApi, thirdPartiesApi } from "@/lib/api";
import {
  PERSON_TYPES,
  type City,
  type Country,
  type Department,
  type PersonType,
  type ThirdParty,
} from "@/types/third-party";

export const metadata = {
  title: "Third parties · Accounting Project",
};

interface Props {
  searchParams: Promise<{
    deleted?: string;
    selected?: string;
    search?: string;
    type?: string;
  }>;
}

const EMPTY: Preloaded = {
  addressDepartments: [],
  addressCities: [],
  birthDepartments: [],
  birthCities: [],
  issueCity: null,
  issueCities: [],
};

/**
 * Server Component: everything is fetched here, so the browser never talks to
 * the API nor needs to know its URL.
 */
export default async function ThirdPartiesPage({ searchParams }: Props) {
  const params = await searchParams;
  const showDeleted = params.deleted === "1";
  const search = params.search ?? "";
  const personType = PERSON_TYPES.includes(params.type as PersonType)
    ? (params.type as PersonType)
    : "";
  const selectedId = Number(params.selected) || null;

  let thirdParties: ThirdParty[] = [];
  let selected: ThirdParty | null = null;
  let countries: Country[] = [];
  let departments: Department[] = [];
  let preloaded = EMPTY;
  let loadError: string | null = null;

  try {
    [thirdParties, countries] = await Promise.all([
      thirdPartiesApi.list({
        search: search || undefined,
        person_type: personType || undefined,
        include_deleted: showDeleted || undefined,
        limit: 200,
      }),
      locationsApi.countries(),
    ]);

    const colombia = countries.find((country) => country.iso_code === "CO");
    if (colombia) {
      departments = await locationsApi.departments({
        country_id: colombia.id,
        limit: 100,
      });
    }

    if (selectedId !== null) {
      selected = await thirdPartiesApi.get(selectedId, true);
      preloaded = await preload(selected);
    }
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ThirdPartiesWorkspace
      thirdParties={thirdParties}
      selected={selected}
      preloaded={preloaded}
      countries={countries}
      departments={departments}
      loadError={loadError}
      showDeleted={showDeleted}
      search={search}
      personType={personType}
    />
  );
}

/**
 * The lists behind the selected third party's cascades.
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
    return await locationsApi.cities({ department_id: departmentId, limit: 200 });
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

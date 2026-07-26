import type { Preloaded } from "@/components/ThirdPartyForm";
import { ThirdPartyPage } from "@/components/ThirdPartyPage";
import { ApiError, locationsApi } from "@/lib/api";
import type { Country, Department } from "@/types/third-party";

export const metadata = {
  title: "New third party · Accounting Project",
};

const EMPTY: Preloaded = {
  addressDepartments: [],
  addressCities: [],
  birthDepartments: [],
  birthCities: [],
  issueCity: null,
  issueCities: [],
};

export default async function NewThirdPartyPage() {
  let countries: Country[] = [];
  let departments: Department[] = [];
  let loadError: string | null = null;

  try {
    countries = await locationsApi.countries();
    const colombia = countries.find((country) => country.iso_code === "CO");
    if (colombia) {
      departments = await locationsApi.departments({
        country_id: colombia.id,
        limit: 100,
      });
    }
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ThirdPartyPage
      thirdParty={null}
      countries={countries}
      departments={departments}
      preloaded={EMPTY}
      loadError={loadError}
    />
  );
}

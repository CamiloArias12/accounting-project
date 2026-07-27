"use server";

import { locationsApi } from "@/lib/api";
import type { City, Department } from "@/types/third-party";

// Lookups for the cascading place pickers.

export async function fetchDepartments(countryId: number): Promise<Department[]> {
  try {
    return await locationsApi.departments({ country_id: countryId, limit: 100 });
  } catch {
    return [];
  }
}

export async function fetchCities(departmentId: number): Promise<City[]> {
  try {
    return await locationsApi.cities({ department_id: departmentId, limit: 200 });
  } catch {
    return [];
  }
}

export async function searchCities(search: string): Promise<City[]> {
  const query = search.trim();
  if (query.length < 2) return [];

  try {
    return await locationsApi.cities({ search: query, limit: 50 });
  } catch {
    return [];
  }
}

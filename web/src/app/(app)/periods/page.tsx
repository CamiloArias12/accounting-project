import { PeriodsGrid } from "@/components/PeriodsGrid";
import { ApiError, periodsApi } from "@/lib/api";
import type { Period } from "@/types/voucher";

export const metadata = {
  title: "Accounting periods · Accounting Project",
};

interface Props {
  searchParams: Promise<{ year?: string }>;
}

export default async function PeriodsPage({ searchParams }: Props) {
  const asked = Number((await searchParams).year);
  const year = Number.isInteger(asked) && asked > 1900 && asked < 3000
    ? asked
    : new Date().getFullYear();

  let periods: Period[] = [];
  let loadError: string | null = null;

  try {
    periods = await periodsApi.year(year);
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return <PeriodsGrid year={year} periods={periods} loadError={loadError} />;
}

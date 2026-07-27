import { ExogenaView } from "@/components/ExogenaView";
import { ApiError, exogenaApi, uvtApi, vouchersApi } from "@/lib/api";
import type { Generation, UvtRun, UvtValue } from "@/types/exogena";
import type { Company } from "@/types/voucher";

export const metadata = {
  title: "Exógena · Accounting Project",
};

const NO_COMPANY: Company = {
  nit: "",
  legal_name: "",
  address: null,
  phone: null,
  email: null,
};

export default async function ExogenaPage() {
  let generations: Generation[] = [];
  let values: UvtValue[] = [];
  let runs: UvtRun[] = [];
  let company = NO_COMPANY;
  let loadError: string | null = null;

  try {
    // The company is one of the three parameters of a filing, even though it
    [generations, values, runs, company] = await Promise.all([
      exogenaApi.history(),
      uvtApi.values(),
      uvtApi.runs(),
      vouchersApi.company(),
    ]);
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ExogenaView
      generations={generations}
      values={values}
      runs={runs}
      company={company}
      defaultYear={new Date().getFullYear() - 1}
      loadError={loadError}
    />
  );
}

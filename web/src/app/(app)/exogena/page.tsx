import { ExogenaView } from "@/components/ExogenaView";
import { ApiError, exogenaApi, uvtApi } from "@/lib/api";
import type { Generation, UvtRun, UvtValue } from "@/types/exogena";

export const metadata = {
  title: "Exógena · Accounting Project",
};

export default async function ExogenaPage() {
  let generations: Generation[] = [];
  let values: UvtValue[] = [];
  let runs: UvtRun[] = [];
  let loadError: string | null = null;

  try {
    [generations, values, runs] = await Promise.all([
      exogenaApi.history(),
      uvtApi.values(),
      uvtApi.runs(),
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
      defaultYear={new Date().getFullYear() - 1}
      loadError={loadError}
    />
  );
}

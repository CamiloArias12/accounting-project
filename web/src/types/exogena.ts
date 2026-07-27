// Amounts arrive as decimal strings, as everywhere else: money is never a float.

export interface Generation {
  id: number;
  year: number;
  threshold_uvt: string;
  uvt_value: string | null;
  threshold_pesos: string;
  filer_nit: string;
  filer_name: string;
  record_count: number;
  total_gross: string;
  total_withheld: string;
  excluded_count: number;
  filename: string;
  generated_at: string;
  generated_by_user_id: number | null;
}

export type UvtSource = "Fetched" | "Manual";

export interface UvtValue {
  year: number;
  value: string;
  source: UvtSource;
  provider: string | null;
  fetched_at: string | null;
}

export type RunStatus = "Succeeded" | "Failed" | "Skipped";

export interface UvtRun {
  id: number;
  year: number;
  status: RunStatus;
  provider: string;
  attempts: number;
  value: string | null;
  detail: string | null;
  started_at: string;
  finished_at: string;
  duration_ms: number;
}

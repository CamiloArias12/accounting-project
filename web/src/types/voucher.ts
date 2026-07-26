/**
 * The English values are the contract with the API, which ships them verbatim.
 * Only the labels shown to the user are translated.
 *
 * Every amount is a string, never a number: see `lib/money`.
 */

export const VOUCHER_STATUSES = ["Draft", "Posted"] as const;
export type VoucherStatus = (typeof VOUCHER_STATUSES)[number];

export const PERIOD_STATUSES = ["Open", "Closed"] as const;
export type PeriodStatus = (typeof PERIOD_STATUSES)[number];

export interface Company {
  nit: string;
  legal_name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
}

export interface VoucherLine {
  id: number;
  line_number: number;
  account_code: string;
  third_party_id: number | null;
  debit: string;
  credit: string;
  description: string | null;
}

export interface Voucher {
  id: number;
  /** Null while it is a draft: only posting takes a consecutive number. */
  number: number | null;
  date: string;
  period_year: number;
  period_month: number;
  description: string;
  status: VoucherStatus;
  posted_at: string | null;
  created_by_user_id: number | null;
  posted_by_user_id: number | null;
  reverses_voucher_id: number | null;
  is_reversal: boolean;
  is_reversed: boolean;
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
  lines: VoucherLine[];
}

export interface VoucherLineInput {
  account_code: string;
  third_party_id?: number | null;
  debit?: string;
  credit?: string;
  description?: string | null;
}

export interface VoucherCreate {
  date: string;
  description: string;
  period_year?: number | null;
  period_month?: number | null;
  lines: VoucherLineInput[];
}

export type VoucherUpdate = Partial<VoucherCreate>;

export interface VoucherReverse {
  date?: string | null;
  description?: string | null;
}

export interface VoucherListParams {
  status?: VoucherStatus;
  period_year?: number;
  period_month?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface Period {
  year: number;
  month: number;
  status: PeriodStatus;
  changed_at: string | null;
  changed_by_user_id: number | null;
}

export interface LedgerAccount {
  code: string;
  name: string;
  nature: string;
  opening_balance: string;
  debit: string;
  credit: string;
  closing_balance: string;
}

export interface LedgerTotals {
  debit: string;
  credit: string;
  balance: string;
  is_balanced: boolean;
}

export interface LedgerReport {
  date_from: string | null;
  date_to: string | null;
  accounts: LedgerAccount[];
  totals: LedgerTotals;
}

export interface LedgerEntry {
  voucher_id: number;
  voucher_number: number | null;
  date: string;
  period_year: number;
  period_month: number;
  description: string;
  third_party_id: number | null;
  debit: string;
  credit: string;
  running_balance: string;
  reverses_voucher_id: number | null;
}

export interface AccountLedger {
  code: string;
  name: string;
  nature: string;
  date_from: string | null;
  date_to: string | null;
  opening_balance: string;
  entries: LedgerEntry[];
  debit: string;
  credit: string;
  closing_balance: string;
}

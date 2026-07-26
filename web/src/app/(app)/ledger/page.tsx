import { LedgerView } from "@/components/LedgerView";
import { ApiError, ledgerApi } from "@/lib/api";
import type { AccountLedger, LedgerReport } from "@/types/voucher";

export const metadata = {
  title: "Ledger · Accounting Project",
};

interface Props {
  searchParams: Promise<{
    date_from?: string;
    date_to?: string;
    account?: string;
  }>;
}

const EMPTY: LedgerReport = {
  date_from: null,
  date_to: null,
  accounts: [],
  totals: { debit: "0.00", credit: "0.00", balance: "0.00", is_balanced: true },
};

export default async function LedgerPage({ searchParams }: Props) {
  const params = await searchParams;
  const dateFrom = params.date_from ?? "";
  const dateTo = params.date_to ?? "";
  const account = params.account ?? "";

  let report = EMPTY;
  let detail: AccountLedger | null = null;
  let loadError: string | null = null;

  const range = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  try {
    // The detail replaces the report rather than sitting beside it: one account
    // at a time is how a ledger is read.
    if (account) detail = await ledgerApi.account(account, range);
    else report = await ledgerApi.report(range);
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <LedgerView
      report={report}
      detail={detail}
      dateFrom={dateFrom}
      dateTo={dateTo}
      loadError={loadError}
    />
  );
}

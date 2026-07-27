import { LedgerView } from "@/components/LedgerView";
import { ApiError, accountsApi, ledgerApi, thirdPartiesApi } from "@/lib/api";
import type { AccountLedger, LedgerReport } from "@/types/voucher";

export const metadata = {
  title: "Ledger · Accounting Project",
};

interface Props {
  searchParams: Promise<{
    date_from?: string;
    date_to?: string;
    account?: string;
    third_party?: string;
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
  const thirdParty = params.third_party ?? "";

  let report = EMPTY;
  let detail: AccountLedger | null = null;
  let loadError: string | null = null;

  const filters = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    third_party_id: thirdParty ? Number(thirdParty) : undefined,
  };

  try {
    // The detail replaces the report rather than sitting beside it: one account
    if (account) detail = await ledgerApi.account(account, filters);
    else report = await ledgerApi.report(filters);
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  const [accountLabel, thirdPartyLabel] = await Promise.all([
    describeAccount(account),
    describeThirdParty(thirdParty),
  ]);

  return (
    <LedgerView
      report={report}
      detail={detail}
      dateFrom={dateFrom}
      dateTo={dateTo}
      account={account}
      accountLabel={accountLabel}
      thirdParty={thirdParty}
      thirdPartyLabel={thirdPartyLabel}
      loadError={loadError}
    />
  );
}

async function describeAccount(code: string): Promise<string> {
  if (!code) return "";
  try {
    const found = await accountsApi.get(code);
    return `${found.code} · ${found.name}`;
  } catch {
    return code;
  }
}

async function describeThirdParty(id: string): Promise<string> {
  if (!id) return "";
  try {
    return (await thirdPartiesApi.get(Number(id))).full_name;
  } catch {
    return id;
  }
}

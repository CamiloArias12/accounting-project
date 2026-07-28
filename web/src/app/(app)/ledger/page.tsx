import { LedgerView } from "@/components/LedgerView";
import { ApiError, accountsApi, ledgerApi, thirdPartiesApi } from "@/lib/api";
import type { AccountLedger } from "@/types/voucher";

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

export default async function LedgerPage({ searchParams }: Props) {
  const params = await searchParams;
  const dateFrom = params.date_from ?? "";
  const dateTo = params.date_to ?? "";
  const account = params.account ?? "";
  const thirdParty = params.third_party ?? "";

  let book: AccountLedger[] = [];
  let loadError: string | null = null;

  try {
    // One view, always the book. Picking an account narrows it instead of
    // switching to something else, and it comes from the same endpoint the
    // spreadsheet is built from.
    book = await ledgerApi.entries({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      third_party_id: thirdParty ? Number(thirdParty) : undefined,
      account_code: account || undefined,
    });
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
      book={book}
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

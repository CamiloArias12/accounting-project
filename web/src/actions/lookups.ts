"use server";

import { accountsApi, ledgerApi, thirdPartiesApi } from "@/lib/api";
import type { Account } from "@/types/account";
import type { ThirdParty } from "@/types/third-party";
import type { AccountLedger } from "@/types/voucher";

// Pickers for the voucher line editor.

export async function searchAccounts(search: string): Promise<Account[]> {
  const query = search.trim();
  if (query.length < 2) return [];

  try {
    const page = await accountsApi.list({
      search: query,
      only_active: true,
      only_postable: true,
      limit: 20,
    });
    return page.items;
  } catch {
    return [];
  }
}

export async function searchThirdParties(search: string): Promise<ThirdParty[]> {
  const query = search.trim();
  if (query.length < 2) return [];

  try {
    const page = await thirdPartiesApi.list({
      search: query,
      only_active: true,
      limit: 20,
    });
    return page.items;
  } catch {
    return [];
  }
}

// The movements behind one account, for the chart on the chart of accounts.
export async function accountHistory(
  code: string,
): Promise<AccountLedger | null> {
  try {
    return await ledgerApi.account(code);
  } catch {
    return null;
  }
}

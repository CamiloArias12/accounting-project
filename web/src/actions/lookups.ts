"use server";

import { accountsApi, thirdPartiesApi } from "@/lib/api";
import type { Account } from "@/types/account";
import type { ThirdParty } from "@/types/third-party";

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

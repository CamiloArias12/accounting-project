"use server";

import { accountsApi, thirdPartiesApi } from "@/lib/api";
import type { Account } from "@/types/account";
import type { ThirdParty } from "@/types/third-party";

/**
 * Pickers for the voucher line editor.
 *
 * Server actions rather than route handlers, so the browser still never learns
 * the API's URL nor holds a token. A failure returns an empty list: an empty
 * dropdown beats a form that unmounts because a lookup threw.
 */

/** Accounts a voucher may be posted to, matched by code or name. */
export async function searchAccounts(search: string): Promise<Account[]> {
  const query = search.trim();
  if (query.length < 2) return [];

  try {
    // Leaves only. Not "level Auxiliar": a six-digit subaccount with nothing
    // under it takes entries too, and offering a heading would only earn a
    // rejection from the server.
    return await accountsApi.list({
      search: query,
      only_active: true,
      only_postable: true,
      limit: 20,
    });
  } catch {
    return [];
  }
}

export async function searchThirdParties(search: string): Promise<ThirdParty[]> {
  const query = search.trim();
  if (query.length < 2) return [];

  try {
    return await thirdPartiesApi.list({
      search: query,
      only_active: true,
      limit: 20,
    });
  } catch {
    return [];
  }
}

import { AccountsWorkspace } from "@/components/AccountsWorkspace";
import { ApiError, accountsApi } from "@/lib/api";
import type { AccountNode } from "@/types/account";

export const metadata = {
  title: "Chart of accounts · Accounting Project",
};

interface Props {
  searchParams: Promise<{ deleted?: string }>;
}

// Server Component: the tree is fetched on the server, so the browser never talks to the API nor needs to know its URL.
export default async function AccountsPage({ searchParams }: Props) {
  const showDeleted = (await searchParams).deleted === "1";

  let tree: AccountNode[] = [];
  let loadError: string | null = null;

  try {
    tree = await accountsApi.tree({ includeDeleted: showDeleted });
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <AccountsWorkspace
      tree={tree}
      loadError={loadError}
      showDeleted={showDeleted}
    />
  );
}

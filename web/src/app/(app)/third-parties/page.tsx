import { ThirdPartyList } from "@/components/ThirdPartyList";
import { ApiError, thirdPartiesApi } from "@/lib/api";
import {
  PERSON_TYPES,
  type PersonType,
  type ThirdParty,
} from "@/types/third-party";

export const metadata = {
  title: "Third parties · Accounting Project",
};

interface Props {
  searchParams: Promise<{
    deleted?: string;
    search?: string;
    type?: string;
    skip?: string;
    limit?: string;
  }>;
}

/** Server Component: the browser never talks to the API nor knows its URL. */
export default async function ThirdPartiesPage({ searchParams }: Props) {
  const params = await searchParams;
  const showDeleted = params.deleted === "1";
  const search = params.search ?? "";
  const personType = PERSON_TYPES.includes(params.type as PersonType)
    ? (params.type as PersonType)
    : "";

  let thirdParties: ThirdParty[] = [];
  let total = 0;
  // Read from the URL rather than fixed in code, so a page size is something
  // a link can carry. Clamped, because the API refuses anything above 500 and
  // a 422 on a mistyped query string is a poor way to find that out.
  const limit = Math.min(500, Math.max(1, Number(params.limit) || 50));
  const skip = Math.max(0, Number(params.skip) || 0);
  let loadError: string | null = null;

  try {
    const page = await thirdPartiesApi.list({
      search: search || undefined,
      person_type: personType || undefined,
      include_deleted: showDeleted || undefined,
      skip,
      limit,
    });
    thirdParties = page.items;
    total = page.total;
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ThirdPartyList
      thirdParties={thirdParties}
      total={total}
      skip={skip}
      limit={limit}
      loadError={loadError}
      showDeleted={showDeleted}
      search={search}
      personType={personType}
    />
  );
}

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
  searchParams: Promise<{ deleted?: string; search?: string; type?: string }>;
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
  let loadError: string | null = null;

  try {
    thirdParties = await thirdPartiesApi.list({
      search: search || undefined,
      person_type: personType || undefined,
      include_deleted: showDeleted || undefined,
      limit: 200,
    });
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <ThirdPartyList
      thirdParties={thirdParties}
      loadError={loadError}
      showDeleted={showDeleted}
      search={search}
      personType={personType}
    />
  );
}

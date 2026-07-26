import { VouchersWorkspace } from "@/components/VouchersWorkspace";
import { ApiError, thirdPartiesApi, vouchersApi } from "@/lib/api";
import {
  VOUCHER_STATUSES,
  type Company,
  type Voucher,
  type VoucherStatus,
} from "@/types/voucher";

export const metadata = {
  title: "Vouchers · Accounting Project",
};

interface Props {
  searchParams: Promise<{
    selected?: string;
    status?: string;
    search?: string;
  }>;
}

const NO_COMPANY: Company = {
  nit: "",
  legal_name: "",
  address: null,
  phone: null,
  email: null,
};

/**
 * Server Component: everything is fetched here, so the browser never talks to
 * the API nor needs to know its URL.
 */
export default async function VouchersPage({ searchParams }: Props) {
  const params = await searchParams;
  const search = params.search ?? "";
  const status = VOUCHER_STATUSES.includes(params.status as VoucherStatus)
    ? (params.status as VoucherStatus)
    : "";
  const selectedId = Number(params.selected) || null;

  let vouchers: Voucher[] = [];
  let selected: Voucher | null = null;
  let company = NO_COMPANY;
  let thirdPartyLabels: Record<number, string> = {};
  let loadError: string | null = null;

  try {
    [vouchers, company] = await Promise.all([
      vouchersApi.list({
        search: search || undefined,
        status: status || undefined,
        limit: 200,
      }),
      vouchersApi.company(),
    ]);

    if (selectedId !== null) {
      selected = await vouchersApi.get(selectedId);
      thirdPartyLabels = await namesOf(selected);
    }
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <VouchersWorkspace
      vouchers={vouchers}
      selected={selected}
      company={company}
      thirdPartyLabels={thirdPartyLabels}
      // Resolved on the server so a new voucher opens dated today without the
      // form having to reach for the clock during render.
      today={new Date().toISOString().slice(0, 10)}
      loadError={loadError}
      status={status}
      search={search}
    />
  );
}

/**
 * The names behind the third party ids on the lines.
 *
 * The voucher stores ids; the pickers show names. Resolving them here keeps the
 * form from opening with a row of bare numbers.
 */
async function namesOf(voucher: Voucher): Promise<Record<number, string>> {
  const ids = [
    ...new Set(
      voucher.lines
        .map((line) => line.third_party_id)
        .filter((id): id is number => id !== null),
    ),
  ];

  const entries = await Promise.all(
    ids.map(async (id) => {
      try {
        const thirdParty = await thirdPartiesApi.get(id, true);
        return [id, thirdParty.full_name] as const;
      } catch {
        return [id, String(id)] as const;
      }
    }),
  );

  return Object.fromEntries(entries);
}

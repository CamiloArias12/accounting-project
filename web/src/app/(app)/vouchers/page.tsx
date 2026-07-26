import { VoucherList } from "@/components/VoucherList";
import { ApiError, vouchersApi } from "@/lib/api";
import {
  VOUCHER_STATUSES,
  type Voucher,
  type VoucherStatus,
} from "@/types/voucher";

export const metadata = {
  title: "Vouchers · Accounting Project",
};

interface Props {
  searchParams: Promise<{ status?: string; search?: string;
    skip?: string;
    limit?: string;
  }>;
}

/** Server Component: the browser never talks to the API nor knows its URL. */
export default async function VouchersPage({ searchParams }: Props) {
  const params = await searchParams;
  const search = params.search ?? "";
  const status = VOUCHER_STATUSES.includes(params.status as VoucherStatus)
    ? (params.status as VoucherStatus)
    : "";

  let vouchers: Voucher[] = [];
  let total = 0;
  // Read from the URL rather than fixed in code, so a page size is something
  // a link can carry. Clamped, because the API refuses anything above 500 and
  // a 422 on a mistyped query string is a poor way to find that out.
  const limit = Math.min(500, Math.max(1, Number(params.limit) || 50));
  const skip = Math.max(0, Number(params.skip) || 0);
  let loadError: string | null = null;

  try {
    const page = await vouchersApi.list({
      search: search || undefined,
      status: status || undefined,
      skip,
      limit,
    });
    vouchers = page.items;
    total = page.total;
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <VoucherList
      vouchers={vouchers}
      total={total}
      skip={skip}
      limit={limit}
      loadError={loadError}
      status={status}
      search={search}
    />
  );
}

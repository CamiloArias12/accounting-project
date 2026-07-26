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
  searchParams: Promise<{ status?: string; search?: string }>;
}

/** Server Component: the browser never talks to the API nor knows its URL. */
export default async function VouchersPage({ searchParams }: Props) {
  const params = await searchParams;
  const search = params.search ?? "";
  const status = VOUCHER_STATUSES.includes(params.status as VoucherStatus)
    ? (params.status as VoucherStatus)
    : "";

  let vouchers: Voucher[] = [];
  let loadError: string | null = null;

  try {
    vouchers = await vouchersApi.list({
      search: search || undefined,
      status: status || undefined,
      limit: 200,
    });
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <VoucherList
      vouchers={vouchers}
      loadError={loadError}
      status={status}
      search={search}
    />
  );
}

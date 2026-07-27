import { notFound } from "next/navigation";

import { VoucherPage } from "@/components/VoucherPage";
import { ApiError, thirdPartiesApi, vouchersApi } from "@/lib/api";
import type { Company, Voucher } from "@/types/voucher";

export const metadata = {
  title: "Voucher · Accounting Project",
};

interface Props {
  params: Promise<{ id: string }>;
}

const NO_COMPANY: Company = {
  nit: "",
  legal_name: "",
  address: null,
  phone: null,
  email: null,
};

export default async function VoucherDetailPage({ params }: Props) {
  const id = Number((await params).id);
  if (!Number.isInteger(id)) notFound();

  let voucher: Voucher | null = null;
  let company = NO_COMPANY;
  let thirdPartyLabels: Record<number, string> = {};
  let loadError: string | null = null;

  try {
    [voucher, company] = await Promise.all([
      vouchersApi.get(id),
      vouchersApi.company(),
    ]);
    thirdPartyLabels = await namesOf(voucher);
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) notFound();
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <VoucherPage
      voucher={voucher}
      company={company}
      thirdPartyLabels={thirdPartyLabels}
      today={new Date().toISOString().slice(0, 10)}
      loadError={loadError}
    />
  );
}

// The names behind the third party ids on the lines.
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

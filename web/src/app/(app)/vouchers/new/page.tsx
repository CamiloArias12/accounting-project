import { VoucherPage } from "@/components/VoucherPage";
import { ApiError, vouchersApi } from "@/lib/api";
import type { Company } from "@/types/voucher";

export const metadata = {
  title: "New voucher · Accounting Project",
};

const NO_COMPANY: Company = {
  nit: "",
  legal_name: "",
  address: null,
  phone: null,
  email: null,
};

export default async function NewVoucherPage() {
  let company = NO_COMPANY;
  let loadError: string | null = null;

  try {
    company = await vouchersApi.company();
  } catch (caught) {
    loadError =
      caught instanceof ApiError ? caught.message : "Could not reach the API";
  }

  return (
    <VoucherPage
      voucher={null}
      company={company}
      thirdPartyLabels={{}}
      // Resolved on the server so a new voucher opens dated today without the
      // form reaching for the clock during render.
      today={new Date().toISOString().slice(0, 10)}
      loadError={loadError}
    />
  );
}

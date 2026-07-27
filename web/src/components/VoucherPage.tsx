"use client";

import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { LoadError, PageShell } from "@/components/PageHeader";
import { VoucherForm } from "@/components/VoucherForm";
import { Button } from "@/components/ui/button";
import type { Company, Voucher } from "@/types/voucher";

interface Props {
  voucher: Voucher | null;
  company: Company;
  thirdPartyLabels: Record<number, string>;
  today: string;
  loadError: string | null;
}

// The shell both the new and the detail routes render the form inside.
export function VoucherPage({
  voucher,
  company,
  thirdPartyLabels,
  today,
  loadError,
}: Props) {
  const t = useTranslations("vouchers");
  const router = useRouter();

  return (
    <PageShell>
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 self-start text-muted-foreground"
        nativeButton={false}
        render={<Link href="/vouchers" />}
      >
        <ArrowLeft />
        {t("backToList")}
      </Button>

      {loadError && <LoadError message={loadError} />}

      <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-border sm:p-6">
        <VoucherForm
          voucher={voucher}
          company={company}
          thirdPartyLabels={thirdPartyLabels}
          today={today}
          onCancel={() => router.push("/vouchers")}
        />
      </div>
    </PageShell>
  );
}

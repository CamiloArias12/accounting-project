"use client";

import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { VoucherForm } from "@/components/VoucherForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Company, Voucher } from "@/types/voucher";

interface Props {
  voucher: Voucher | null;
  company: Company;
  thirdPartyLabels: Record<number, string>;
  today: string;
  loadError: string | null;
}

/** The shell both the new and the detail routes render the form inside. */
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
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <Button
        variant="ghost"
        size="sm"
        className="self-start"
        // `nativeButton={false}`: this renders an <a>, and Base UI warns when a
        // component styled as a button is not one — the semantics differ.
        nativeButton={false}
        render={<Link href="/vouchers" />}
      >
        <ArrowLeft />
        {t("backToList")}
      </Button>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {loadError}
        </p>
      )}

      <Card>
        <CardContent>
          <VoucherForm
            voucher={voucher}
            company={company}
            thirdPartyLabels={thirdPartyLabels}
            today={today}
            onCancel={() => router.push("/vouchers")}
          />
        </CardContent>
      </Card>
    </main>
  );
}

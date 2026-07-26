"use client";

import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { LoadError, PageShell } from "@/components/PageHeader";
import type { Preloaded } from "@/components/ThirdPartyForm";
import { ThirdPartyForm } from "@/components/ThirdPartyForm";
import { Button } from "@/components/ui/button";
import type { Country, Department, ThirdParty } from "@/types/third-party";

interface Props {
  thirdParty: ThirdParty | null;
  countries: Country[];
  departments: Department[];
  preloaded: Preloaded;
  loadError: string | null;
}

/** The shell both the new and the detail routes render the form inside. */
export function ThirdPartyPage({
  thirdParty,
  countries,
  departments,
  preloaded,
  loadError,
}: Props) {
  const t = useTranslations("thirdParties");
  const router = useRouter();

  return (
    <PageShell className="max-w-4xl">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 self-start text-muted-foreground"
        // `nativeButton={false}`: this renders an <a>, and Base UI warns when a
        // component styled as a button is not one — the semantics differ.
        nativeButton={false}
        render={<Link href="/third-parties" />}
      >
        <ArrowLeft />
        {t("backToList")}
      </Button>

      {loadError && <LoadError message={loadError} />}

      <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-border sm:p-6">
        <ThirdPartyForm
          thirdParty={thirdParty}
          countries={countries}
          departments={departments}
          preloaded={preloaded}
          onCancel={() => router.push("/third-parties")}
        />
      </div>
    </PageShell>
  );
}

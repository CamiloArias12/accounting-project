"use client";

import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { Preloaded } from "@/components/ThirdPartyForm";
import { ThirdPartyForm } from "@/components/ThirdPartyForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <Button
        variant="ghost"
        size="sm"
        className="self-start"
        // `nativeButton={false}`: this renders an <a>, and Base UI warns when a
        // component styled as a button is not one — the semantics differ.
        nativeButton={false}
        render={<Link href="/third-parties" />}
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
          <ThirdPartyForm
            thirdParty={thirdParty}
            countries={countries}
            departments={departments}
            preloaded={preloaded}
            onCancel={() => router.push("/third-parties")}
          />
        </CardContent>
      </Card>
    </main>
  );
}

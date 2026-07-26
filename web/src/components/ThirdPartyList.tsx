"use client";

import { Eye, EyeOff, Plus, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchableSelect } from "@/components/SearchableSelect";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PERSON_TYPES, type ThirdParty } from "@/types/third-party";

interface Props {
  thirdParties: ThirdParty[];
  total: number;
  skip: number;
  limit: number;
  loadError: string | null;
  showDeleted: boolean;
  search: string;
  personType: string;
}

/** The list on its own page; the form lives at `/third-parties/new` and `/[id]`. */
export function ThirdPartyList({
  thirdParties,
  total,
  skip,
  limit,
  loadError,
  showDeleted,
  search,
  personType,
}: Props) {
  const t = useTranslations("thirdParties");
  const router = useRouter();
  const params = useSearchParams();

  function go(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    // Any filter change goes back to the first page: page four of the old
    // list is not page four of the new one.
    if (key !== "skip") next.delete("skip");
    router.push(`/third-parties?${next}`);
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={
          <>
            {t("count", { count: total })}
            {showDeleted && ` · ${t("includingDeleted")}`}
          </>
        }
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => go("deleted", showDeleted ? "" : "1")}
            >
              {showDeleted ? <EyeOff /> : <Eye />}
              {showDeleted ? t("hideDeleted") : t("showDeleted")}
            </Button>
            {/* `nativeButton={false}`: this renders an <a>, and Base UI warns
                when something styled as a button is not one. */}
            <Button
              nativeButton={false}
              render={<Link href="/third-parties/new" />}
            >
              <Plus />
              {t("newThirdParty")}
            </Button>
          </>
        }
      />

      {loadError && <LoadError message={loadError} />}

      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-card p-2 shadow-xs ring-1 ring-border">
        <div className="relative min-w-56 flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            defaultValue={search}
            placeholder={t("searchPlaceholder")}
            className="pl-8"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                go("search", (event.target as HTMLInputElement).value);
              }
            }}
          />
        </div>
        <SearchableSelect
          className="w-56"
          value={personType || "all"}
          onChange={(value) => go("type", value === "all" ? "" : value)}
          options={[
            { value: "all", label: t("allTypes") },
            ...PERSON_TYPES.map((value) => ({
              value,
              label: t(`personTypes.${value}`),
            })),
          ]}
        />
      </div>

      <div className="overflow-hidden rounded-xl bg-card shadow-sm ring-1 ring-border">
        <div className="scrollbar-slim overflow-x-auto">
          <Table className="min-w-[40rem]">
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="w-40 pl-4">
                  {t("columnDocument")}
                </TableHead>
                <TableHead>{t("columnName")}</TableHead>
                <TableHead className="w-44">{t("columnType")}</TableHead>
                <TableHead className="w-32 pr-4">{t("columnState")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {thirdParties.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={4}
                    className="py-14 text-center text-muted-foreground"
                  >
                    {t("empty")}
                  </TableCell>
                </TableRow>
              )}
              {thirdParties.map((thirdParty) => (
                <TableRow
                  key={thirdParty.id}
                  onClick={() => router.push(`/third-parties/${thirdParty.id}`)}
                  className="cursor-pointer"
                >
                  <TableCell className="pl-4 font-mono text-xs text-muted-foreground">
                    {thirdParty.formatted_document}
                  </TableCell>
                  <TableCell
                    className={
                      thirdParty.deleted_at
                        ? "line-through opacity-60"
                        : "font-medium"
                    }
                  >
                    {thirdParty.full_name}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {t(`personTypes.${thirdParty.person_type}`)}
                  </TableCell>
                  <TableCell className="pr-4">
                    {thirdParty.deleted_at ? (
                      <Badge variant="destructive">{t("deletedBadge")}</Badge>
                    ) : thirdParty.is_active ? null : (
                      <Badge variant="secondary">{t("inactiveBadge")}</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <Pagination
        total={total}
        skip={skip}
        limit={limit}
        onChange={(next) => go("skip", next === 0 ? "" : String(next))}
      />
    </PageShell>
  );
}

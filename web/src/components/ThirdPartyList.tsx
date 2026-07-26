"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  loadError: string | null;
  showDeleted: boolean;
  search: string;
  personType: string;
}

/** The list on its own page; the form lives at `/third-parties/new` and `/[id]`. */
export function ThirdPartyList({
  thirdParties,
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
    router.push(`/third-parties?${next}`);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("count", { count: thirdParties.length })}
            {showDeleted && ` · ${t("includingDeleted")}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => go("deleted", showDeleted ? "" : "1")}
          >
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
        </div>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {loadError}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Input
          defaultValue={search}
          placeholder={t("searchPlaceholder")}
          className="max-w-sm"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              go("search", (event.target as HTMLInputElement).value);
            }
          }}
        />
        <Select
          value={personType || "all"}
          onValueChange={(value) =>
            go("type", !value || value === "all" ? "" : String(value))
          }
        >
          <SelectTrigger className="w-56">
            <SelectValue>
              {(value: string) =>
                value === "all" ? t("allTypes") : t(`personTypes.${value}`)
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("allTypes")}</SelectItem>
            {PERSON_TYPES.map((value) => (
              <SelectItem key={value} value={value}>
                {t(`personTypes.${value}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <Table className="min-w-[40rem]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-40">{t("columnDocument")}</TableHead>
              <TableHead>{t("columnName")}</TableHead>
              <TableHead className="w-44">{t("columnType")}</TableHead>
              <TableHead className="w-32">{t("columnState")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {thirdParties.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="py-10 text-center text-muted-foreground"
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
                <TableCell className="font-mono text-xs">
                  {thirdParty.formatted_document}
                </TableCell>
                <TableCell
                  className={
                    thirdParty.deleted_at ? "line-through opacity-60" : ""
                  }
                >
                  {thirdParty.full_name}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {t(`personTypes.${thirdParty.person_type}`)}
                </TableCell>
                <TableCell>
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
    </main>
  );
}

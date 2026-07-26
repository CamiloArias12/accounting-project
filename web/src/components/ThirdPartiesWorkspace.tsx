"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ThirdPartyForm, type Preloaded } from "@/components/ThirdPartyForm";
import { ThirdPartyList } from "@/components/ThirdPartyList";
import {
  PERSON_TYPES,
  type Country,
  type Department,
  type ThirdParty,
} from "@/types/third-party";

interface Props {
  thirdParties: ThirdParty[];
  selected: ThirdParty | null;
  preloaded: Preloaded;
  countries: Country[];
  departments: Department[];
  loadError: string | null;
  showDeleted: boolean;
  search: string;
  personType: string;
}

/**
 * Selection lives in the URL, not in component state.
 *
 * The form needs the department and city lists of whoever is selected, and only
 * the server can resolve those. Navigating on selection keeps the form and its
 * preloaded lists in step; keeping it in state would show the previous person's
 * municipalities under the new one's department.
 */
export function ThirdPartiesWorkspace({
  thirdParties,
  selected,
  preloaded,
  countries,
  departments,
  loadError,
  showDeleted,
  search,
  personType,
}: Props) {
  const t = useTranslations("thirdParties");
  const router = useRouter();
  const params = useSearchParams();

  const [query, setQuery] = useState(search);

  // Debounced so typing does not fire a request per keystroke.
  useEffect(() => {
    if (query === search) return;

    const timer = setTimeout(() => {
      router.replace(`/third-parties?${withParam("search", query)}`);
    }, 300);
    return () => clearTimeout(timer);
    // `search` is what the server currently reflects; comparing against it is
    // what stops the effect from looping on its own navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, search]);

  function withParam(key: string, value: string): string {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    // Any filter change invalidates which row was selected.
    if (key !== "selected") next.delete("selected");
    return next.toString();
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6 pt-16 lg:pt-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("count", { count: thirdParties.length })}
            {showDeleted && ` · ${t("includingDeleted")}`}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              router.push(`/third-parties?${withParam("selected", "")}`)
            }
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
          >
            {t("newThirdParty")}
          </button>
          <button
            type="button"
            onClick={() =>
              router.push(
                `/third-parties?${withParam("deleted", showDeleted ? "" : "1")}`,
              )
            }
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            {showDeleted ? t("hideDeleted") : t("showDeleted")}
          </button>
        </div>
      </header>

      {loadError && (
        <p
          role="alert"
          className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-400"
        >
          {loadError}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_34rem]">
        <section className="min-w-0 rounded-lg border border-border">
          <div className="flex flex-wrap gap-2 border-b border-border p-3">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("searchPlaceholder")}
              className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-1.5 text-sm"
            />
            <select
              value={personType}
              onChange={(event) =>
                router.replace(
                  `/third-parties?${withParam("type", event.target.value)}`,
                )
              }
              className="rounded-md border border-border bg-transparent px-3 py-1.5 text-sm"
            >
              <option value="">{t("allTypes")}</option>
              {PERSON_TYPES.map((value) => (
                <option key={value} value={value}>
                  {t(`personTypes.${value}`)}
                </option>
              ))}
            </select>
          </div>

          <div className="max-h-[70vh] overflow-y-auto">
            <ThirdPartyList
              thirdParties={thirdParties}
              selectedId={selected?.id ?? null}
              onSelect={(thirdParty) =>
                router.push(
                  `/third-parties?${withParam("selected", String(thirdParty.id))}`,
                )
              }
            />
          </div>
        </section>

        <aside className="rounded-lg border border-border p-4">
          <ThirdPartyForm
            // Remounting on a different selection resets the form without effects.
            key={selected?.id ?? "new"}
            thirdParty={selected}
            countries={countries}
            departments={departments}
            preloaded={preloaded}
            onCancel={() =>
              router.push(`/third-parties?${withParam("selected", "")}`)
            }
          />
        </aside>
      </div>
    </main>
  );
}

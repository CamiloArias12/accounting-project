import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/PageHeader";
import { cn } from "@/lib/utils";

/** A grey block standing in for content that has not arrived yet. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded-md bg-muted", className)} />
  );
}

/**
 * What a screen shows while its data is on the way.
 *
 * The pages are Server Components, so a navigation waits on the API before
 * anything renders — the ledger with a date range over a year of movements
 * takes long enough that a frozen screen reads as a broken click. Rendered
 * from `loading.tsx`, this is the Suspense fallback React shows in the
 * meantime.
 *
 * It mirrors the real layout rather than showing a spinner: a header, a row of
 * filters and a table are what is coming, so the page does not jump when it
 * arrives.
 */
export async function PageSkeleton({ rows = 6 }: { rows?: number }) {
  const t = await getTranslations("status");

  return (
    <PageShell>
      {/* One live region for the whole page: a screen reader announces "loading"
          once, not once per grey block. */}
      <div role="status" aria-live="polite" className="sr-only">
        {t("loading")}
      </div>

      <div aria-hidden className="flex flex-col gap-6">
        <div className="space-y-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-80" />
        </div>

        <div className="flex flex-wrap gap-3 rounded-xl bg-card p-3 shadow-xs ring-1 ring-border">
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-9 w-56" />
        </div>

        <div className="flex flex-col gap-2 rounded-xl bg-card p-4 shadow-xs ring-1 ring-border">
          {Array.from({ length: rows }, (_, row) => (
            <Skeleton key={row} className="h-9 w-full" />
          ))}
        </div>
      </div>
    </PageShell>
  );
}

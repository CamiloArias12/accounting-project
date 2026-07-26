"use client";

import { Download, FileCode2, Hand, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";
import { toast } from "sonner";

import { generateExogena, refreshUvt, setUvt } from "@/actions/exogena";
import { IDLE, type FormState } from "@/actions/state";
import { LoadError, PageHeader, PageShell } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import { cn } from "@/lib/utils";
import type { Generation, UvtRun, UvtValue } from "@/types/exogena";

interface Props {
  generations: Generation[];
  values: UvtValue[];
  runs: UvtRun[];
  /** The taxable year the forms open on: the one just ended. */
  defaultYear: number;
  loadError: string | null;
}

export function ExogenaView({
  generations,
  values,
  runs,
  defaultYear,
  loadError,
}: Props) {
  const t = useTranslations("exogena");

  return (
    <PageShell className="max-w-6xl">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("subtitle")}
      />

      {loadError && <LoadError message={loadError} />}

      <GenerateCard defaultYear={defaultYear} />
      <GenerationsCard generations={generations} />
      <UvtCard values={values} runs={runs} defaultYear={defaultYear} />
    </PageShell>
  );
}

/** The form that builds a report. */
function GenerateCard({ defaultYear }: { defaultYear: number }) {
  const t = useTranslations("exogena");
  const [state, submit] = useActionState<FormState, FormData>(
    generateExogena,
    IDLE,
  );
  useAnnounce(state);

  return (
    <Card
      icon={<FileCode2 className="size-5" />}
      title={t("generateTitle")}
      description={t("generateHelp")}
    >
      <form action={submit} className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="exogena-year">{t("year")}</Label>
          <Input
            id="exogena-year"
            name="year"
            type="number"
            defaultValue={defaultYear}
            className="w-28 tabular-nums"
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="exogena-threshold">{t("thresholdUvt")}</Label>
          <Input
            id="exogena-threshold"
            name="threshold_uvt"
            inputMode="decimal"
            defaultValue="0"
            placeholder="0"
            className="w-32 text-right tabular-nums"
          />
        </div>

        <Submit label={t("generate")} pendingLabel={t("generating")} />
      </form>

      {/* The rule that makes the screen usable for a year the DIAN has not
          published a UVT for: zero means no threshold, so no UVT is needed. */}
      <p className="text-xs text-muted-foreground">{t("thresholdHelp")}</p>
    </Card>
  );
}

function GenerationsCard({ generations }: { generations: Generation[] }) {
  const t = useTranslations("exogena");

  return (
    <Card title={t("historyTitle")} description={t("historyHelp")}>
      {generations.length === 0 ? (
        <Empty label={t("noGenerations")} />
      ) : (
        <Scroller minWidth="52rem">
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead className="pl-4">{t("year")}</TableHead>
              <TableHead className="text-right">{t("threshold")}</TableHead>
              <TableHead className="text-right">{t("records")}</TableHead>
              <TableHead className="text-right">{t("excluded")}</TableHead>
              <TableHead className="text-right">{t("gross")}</TableHead>
              <TableHead className="text-right">{t("withheld")}</TableHead>
              <TableHead>{t("generatedAt")}</TableHead>
              <TableHead className="pr-4" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {generations.map((generation) => (
              <TableRow key={generation.id}>
                <TableCell className="pl-4 font-medium tabular-nums">
                  {generation.year}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {/* The UVT count and what it came to in pesos: the second is
                      the number the rows were actually measured against. */}
                  {Number(generation.threshold_uvt) === 0
                    ? "—"
                    : `${generation.threshold_uvt} UVT · ${formatMoney(
                        generation.threshold_pesos,
                      )}`}
                </TableCell>
                <TableCell className="text-right font-medium tabular-nums">
                  {generation.record_count}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {generation.excluded_count}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(generation.total_gross)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(generation.total_withheld)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {generation.generated_at.slice(0, 16).replace("T", " ")}
                </TableCell>
                <TableCell className="pr-4 text-right">
                  {/* A link, not a fetch: the browser saves the file and the
                      token never leaves the server. Styled rather than rendered
                      through `Button`, which would put `role="button"` on an
                      anchor that navigates. */}
                  <a
                    href={`/exogena/${generation.id}/file`}
                    download={generation.filename}
                    className={cn(
                      buttonVariants({ variant: "outline", size: "sm" }),
                    )}
                  >
                    <Download />
                    {t("download")}
                  </a>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Scroller>
      )}
    </Card>
  );
}

/**
 * The UVT the threshold is measured in.
 *
 * Three things on one card because they are one subject: what is stored, how to
 * go and get it, and what happened the last few times we tried.
 */
function UvtCard({
  values,
  runs,
  defaultYear,
}: {
  values: UvtValue[];
  runs: UvtRun[];
  defaultYear: number;
}) {
  const t = useTranslations("exogena");
  const router = useRouter();

  const [refreshState, submitRefresh] = useActionState<FormState, FormData>(
    refreshUvt,
    IDLE,
  );
  const [manualState, submitManual] = useActionState<FormState, FormData>(
    setUvt,
    IDLE,
  );
  useAnnounce(refreshState);
  useAnnounce(manualState);

  return (
    <Card title={t("uvtTitle")} description={t("uvtHelp")}>
      <div className="flex flex-wrap items-end gap-6">
        <form action={submitRefresh} className="flex items-end gap-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="uvt-fetch-year">{t("fetchYear")}</Label>
            <Input
              id="uvt-fetch-year"
              name="year"
              type="number"
              defaultValue={defaultYear}
              className="w-28 tabular-nums"
              required
            />
          </div>
          <Submit
            label={t("fetch")}
            pendingLabel={t("fetching")}
            variant="outline"
            icon={<RefreshCw />}
          />
        </form>

        <form action={submitManual} className="flex items-end gap-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="uvt-manual-year">{t("manualYear")}</Label>
            <Input
              id="uvt-manual-year"
              name="year"
              type="number"
              defaultValue={defaultYear}
              className="w-28 tabular-nums"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="uvt-manual-value">{t("manualValue")}</Label>
            <Input
              id="uvt-manual-value"
              name="value"
              inputMode="decimal"
              placeholder="49799.00"
              className="w-36 text-right tabular-nums"
              required
            />
          </div>
          <Submit
            label={t("save")}
            pendingLabel={t("saving")}
            variant="outline"
            icon={<Hand />}
          />
        </form>
      </div>

      {/* A refresh answers before it has run, so the table it lands in has to be
          asked for again — the page has no way to know when it finished. */}
      <div>
        <Button variant="ghost" size="sm" onClick={() => router.refresh()}>
          <RefreshCw />
          {t("reload")}
        </Button>
      </div>

      {values.length === 0 ? (
        <Empty label={t("noValues")} />
      ) : (
        <Scroller minWidth="36rem">
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead className="pl-4">{t("year")}</TableHead>
              <TableHead className="text-right">{t("value")}</TableHead>
              <TableHead>{t("source")}</TableHead>
              <TableHead className="pr-4">{t("fetchedAt")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {values.map((value) => (
              <TableRow key={value.year}>
                <TableCell className="pl-4 font-medium tabular-nums">
                  {value.year}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(value.value)}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={value.source === "Manual" ? "outline" : "secondary"}
                  >
                    {t(`sources.${value.source}`)}
                  </Badge>
                  {value.provider && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {value.provider}
                    </span>
                  )}
                </TableCell>
                <TableCell className="pr-4 text-muted-foreground">
                  {value.fetched_at
                    ? value.fetched_at.slice(0, 16).replace("T", " ")
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Scroller>
      )}

      {runs.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium">{t("runsTitle")}</h3>
          {/* The failures are the point: a threshold that quietly used a stale
              UVT because a fetch died is what this list makes visible. */}
          <ul className="flex flex-col gap-1.5 text-xs">
            {runs.map((run) => (
              <li key={run.id} className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "inline-block size-1.5 shrink-0 rounded-full",
                    run.status === "Succeeded" && "bg-success",
                    run.status === "Failed" && "bg-destructive",
                    run.status === "Skipped" && "bg-muted-foreground",
                  )}
                  aria-hidden
                />
                <span className="font-medium tabular-nums">{run.year}</span>
                <span className="text-muted-foreground">
                  {t(`statuses.${run.status}`)} · {run.provider} ·{" "}
                  {t("attempts", { count: run.attempts })} · {run.duration_ms}ms
                </span>
                {run.detail && (
                  <span className="text-muted-foreground">— {run.detail}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// --- the pieces the cards are made of ---------------------------------------

function Card({
  icon,
  title,
  description,
  children,
}: {
  icon?: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 rounded-xl bg-card p-4 shadow-xs ring-1 ring-border sm:p-5">
      <header className="flex items-start gap-3">
        {icon && (
          <span
            aria-hidden
            className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15"
          >
            {icon}
          </span>
        )}
        <div>
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

function Scroller({
  minWidth,
  children,
}: {
  minWidth: string;
  children: React.ReactNode;
}) {
  return (
    <div className="scrollbar-slim overflow-x-auto rounded-lg ring-1 ring-border">
      <Table style={{ minWidth }}>{children}</Table>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <p className="rounded-lg bg-muted/40 p-8 text-center text-sm text-muted-foreground">
      {label}
    </p>
  );
}

function Submit({
  label,
  pendingLabel,
  variant = "default",
  icon,
}: {
  label: string;
  pendingLabel: string;
  variant?: "default" | "outline";
  icon?: React.ReactNode;
}) {
  const { pending } = useFormStatus();

  return (
    <Button type="submit" variant={variant} disabled={pending}>
      {icon}
      {pending ? pendingLabel : label}
    </Button>
  );
}

function useAnnounce(state: FormState) {
  useEffect(() => {
    if (state.status === "success") toast.success(state.message);
    if (state.status === "error") toast.error(state.message);
  }, [state]);
}

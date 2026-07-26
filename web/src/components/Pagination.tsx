"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

interface Props {
  total: number;
  skip: number;
  limit: number;
  onChange: (skip: number) => void;
}

/**
 * Previous and next over a `skip`/`limit` window.
 *
 * Not numbered pages: those need the page count on screen and a decision about
 * what to do with page 47 of 900. Two buttons and a count of what you are
 * looking at answers the question people actually have — is there more?
 */
export function Pagination({ total, skip, limit, onChange }: Props) {
  const t = useTranslations("pagination");

  const first = total === 0 ? 0 : skip + 1;
  const last = Math.min(skip + limit, total);
  const hasPrevious = skip > 0;
  const hasNext = last < total;

  // Nothing to page through: the controls would be furniture.
  if (total <= limit && !hasPrevious) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="text-sm text-muted-foreground">
        {t("showing", { first, last, total })}
      </p>
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={!hasPrevious}
          onClick={() => onChange(Math.max(0, skip - limit))}
        >
          <ChevronLeft />
          {t("previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!hasNext}
          onClick={() => onChange(skip + limit)}
        >
          {t("next")}
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}

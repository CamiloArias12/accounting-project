"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import { formatMoney, toCents } from "@/lib/money";
import type { AccountLedger } from "@/types/voucher";

// How an account's balance moved over the range.

interface Props {
  detail: AccountLedger;
}

const WIDTH = 900;
const HEIGHT = 220;
const PADDING = { top: 16, right: 16, bottom: 28, left: 96 };

interface Point {
  date: string;
  balance: number;
  x: number;
  y: number;
}

export function BalanceChart({ detail }: Props) {
  const t = useTranslations("ledger");
  const gradientId = useId();

  const series = toSeries(detail);

  if (series.length < 2) {
    return (
      <Frame title={t("chartTitle")}>
        <p className="py-10 text-center text-sm text-muted-foreground">
          {t("chartTooFewPoints")}
        </p>
      </Frame>
    );
  }

  const balances = series.map((point) => point.balance);
  const { scaleX, scaleY, ticks, zeroY } = scales(series, balances);

  const points: Point[] = series.map((entry) => ({
    ...entry,
    x: scaleX(entry.date),
    y: scaleY(entry.balance),
  }));

  const line = points
    .map((point, index) => {
      if (index === 0) return `M ${point.x} ${point.y}`;
      return `L ${point.x} ${points[index - 1].y} L ${point.x} ${point.y}`;
    })
    .join(" ");

  const floor = HEIGHT - PADDING.bottom;
  const area = `${line} L ${points[points.length - 1].x} ${floor} L ${points[0].x} ${floor} Z`;

  return (
    <Frame title={t("chartTitle")}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-56 w-full"
        role="img"
        aria-label={t("chartSummary", {
          from: series[0].date,
          to: series[series.length - 1].date,
          opening: formatMoney(series[0].balance),
          closing: formatMoney(series[series.length - 1].balance),
        })}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.18" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((tick) => (
          <g key={tick.value}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={tick.y}
              y2={tick.y}
              stroke="var(--border)"
              strokeDasharray={tick.value === 0 ? undefined : "3 4"}
            />
            <text
              x={PADDING.left - 10}
              y={tick.y + 4}
              textAnchor="end"
              className="fill-muted-foreground text-[11px] tabular-nums"
            >
              {formatMoney(tick.value)}
            </text>
          </g>
        ))}

        {zeroY !== null && (
          <line
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={zeroY}
            y2={zeroY}
            stroke="var(--muted-foreground)"
            strokeOpacity="0.4"
          />
        )}

        <path d={area} fill={`url(#${gradientId})`} />
        <path
          d={line}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {points.map((point, index) => (
          <circle
            key={`${point.date}-${index}`}
            cx={point.x}
            cy={point.y}
            r="3.5"
            fill="var(--card)"
            stroke="var(--primary)"
            strokeWidth="2"
          >
            <title>{`${point.date} · ${formatMoney(point.balance)}`}</title>
          </circle>
        ))}

        <text
          x={PADDING.left}
          y={HEIGHT - 8}
          className="fill-muted-foreground text-[11px]"
        >
          {series[0].date}
        </text>
        <text
          x={WIDTH - PADDING.right}
          y={HEIGHT - 8}
          textAnchor="end"
          className="fill-muted-foreground text-[11px]"
        >
          {series[series.length - 1].date}
        </text>
      </svg>
    </Frame>
  );
}

function Frame({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl bg-card p-4 shadow-xs ring-1 ring-border">
      <h3 className="text-sm font-medium">{title}</h3>
      {children}
    </section>
  );
}

function toSeries(detail: AccountLedger): Array<{ date: string; balance: number }> {
  const byDay = new Map<string, number>();

  if (detail.date_from) {
    byDay.set(detail.date_from, toCents(detail.opening_balance));
  }

  for (const entry of detail.entries) {
    byDay.set(entry.date, toCents(entry.running_balance));
  }

  return [...byDay]
    .map(([date, balance]) => ({ date, balance }))
    .sort((left, right) => left.date.localeCompare(right.date));
}

function scales(
  series: Array<{ date: string; balance: number }>,
  balances: number[],
) {
  const first = Date.parse(series[0].date);
  const last = Date.parse(series[series.length - 1].date);
  const span = last - first || 1;

  const scaleX = (date: string) =>
    PADDING.left +
    ((Date.parse(date) - first) / span) * (WIDTH - PADDING.left - PADDING.right);

  const highest = Math.max(...balances);
  const lowest = Math.min(...balances);
  const padding = (highest - lowest) * 0.15 || Math.abs(highest) * 0.1 || 1;

  const top = highest + padding;
  const bottom = lowest - padding;
  const range = top - bottom;
  const usable = HEIGHT - PADDING.top - PADDING.bottom;

  const scaleY = (balance: number) =>
    PADDING.top + ((top - balance) / range) * usable;

  const ticks = [top, (top + bottom) / 2, bottom].map((value) => ({
    value: Math.round(value),
    y: scaleY(value),
  }));

  const zeroY = bottom <= 0 && top >= 0 ? scaleY(0) : null;

  return { scaleX, scaleY, ticks, zeroY };
}

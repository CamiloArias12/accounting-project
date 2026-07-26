"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import { formatMoney, toCents } from "@/lib/money";
import type { AccountLedger } from "@/types/voucher";

/**
 * How an account's balance moved over the range.
 *
 * Drawn from the same entries the table below it shows, not from a second
 * endpoint: a chart that disagrees with the numbers printed under it is worse
 * than no chart, and the only way to guarantee they agree is for there to be
 * one source.
 *
 * Hand-drawn SVG rather than a charting library. One line chart does not
 * justify recharts and its d3 dependencies in the bundle, and everything a
 * library would give here — a path, an axis, a hover label — is the code
 * below. If a second or third chart appears, that trade flips.
 */

interface Props {
  detail: AccountLedger;
}

const WIDTH = 900;
const HEIGHT = 220;
const PADDING = { top: 16, right: 16, bottom: 28, left: 96 };

interface Point {
  date: string;
  /** Cents, so the arithmetic here is integer like everywhere else. */
  balance: number;
  x: number;
  y: number;
}

export function BalanceChart({ detail }: Props) {
  const t = useTranslations("ledger");
  const gradientId = useId();

  const series = toSeries(detail);

  // Two points make a line; one makes a dot that says nothing the figure in the
  // header does not already say. Said out loud rather than rendering nothing:
  // a panel that silently disappears reads as a broken feature, not as an
  // account with one movement in it.
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

  // A balance is a step function: it holds its value until the next movement
  // changes it. Interpolating between two entries would draw a slope through
  // days on which nothing happened.
  const line = points
    .map((point, index) => {
      if (index === 0) return `M ${point.x} ${point.y}`;
      // Hold the previous balance until this date, then step to the new one.
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
        // The table underneath carries every figure; this says what shape they
        // make, which is the only thing a screen reader cannot get from it.
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

        {/* Zero is drawn solid where the range crosses it: for a credit account
            the balance is negative throughout, and the line matters. */}
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
            {/* A native SVG title is the browser's own tooltip: no state, no
                event handlers, and it works before the JavaScript loads. */}
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

/** The card the chart sits in, shared with the state where there is no line. */
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

/**
 * The balance at the end of each day that had movement.
 *
 * Several entries can share a date, and only the last of them is the day's
 * closing balance — plotting all of them would draw a vertical scribble where
 * one voucher posted six lines.
 */
function toSeries(detail: AccountLedger): Array<{ date: string; balance: number }> {
  const byDay = new Map<string, number>();

  // The opening balance belongs on the chart: without it a range that starts
  // mid-life looks as though the account started from nothing. Only when a
  // starting date was asked for — with no range there is nothing before, and
  // the opening is zero by definition.
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

  // Positioned by date, not by index: six months between two movements has to
  // look like six months, or the chart tells a story the books do not.
  const scaleX = (date: string) =>
    PADDING.left +
    ((Date.parse(date) - first) / span) * (WIDTH - PADDING.left - PADDING.right);

  // Scaled to the data, not anchored to zero. Forcing zero into the axis is a
  // bar chart's rule, where the bar's length is the value; a balance far from
  // zero — a cash account at 3.500.000 — would spend the whole chart as a flat
  // line at the bottom with its actual movement invisible. The axis labels
  // carry the magnitude, and the zero line is drawn whenever it is in view.
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

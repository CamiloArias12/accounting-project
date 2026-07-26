/**
 * Money as integer cents.
 *
 * The API sends and receives decimals as strings on purpose. Parsing them into
 * JavaScript numbers would put a ledger on binary floating point, where
 * 0.1 + 0.2 is not 0.3 — and an entry that does not balance by a hundredth is
 * refused by the server, so the browser must not invent one.
 *
 * Everything here works in cents, which are integers, and only turns back into
 * a string at the edges.
 */

const CENTS_PER_UNIT = 100;

/** Parses "150000.00" into 15000000 cents. Anything unreadable is zero. */
export function toCents(value: string | null | undefined): number {
  if (!value) return 0;

  const cleaned = value.replace(/[^\d.-]/g, "");
  if (!cleaned || cleaned === "-") return 0;

  const negative = cleaned.startsWith("-");
  const [whole = "0", fraction = ""] = cleaned.replace("-", "").split(".");
  // Two decimals, padded or truncated: the server accepts no more.
  const cents = Number(whole) * CENTS_PER_UNIT + Number(fraction.padEnd(2, "0").slice(0, 2));

  return Number.isFinite(cents) ? (negative ? -cents : cents) : 0;
}

/** Turns 15000000 cents back into "150000.00", which is what the API expects. */
export function fromCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(Math.round(cents));

  return `${sign}${Math.floor(absolute / CENTS_PER_UNIT)}.${String(
    absolute % CENTS_PER_UNIT,
  ).padStart(2, "0")}`;
}

/** For display: "1.234.567,89" in Colombian format. */
export function formatMoney(value: string | number | null | undefined): string {
  const cents = typeof value === "number" ? value : toCents(value);

  return (cents / CENTS_PER_UNIT).toLocaleString("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function sumCents(values: Array<string | null | undefined>): number {
  return values.reduce<number>((total, value) => total + toCents(value), 0);
}

// Money as integer cents.

const CENTS_PER_UNIT = 100;

export function toCents(value: string | null | undefined): number {
  if (!value) return 0;

  const cleaned = value.replace(/[^\d.-]/g, "");
  if (!cleaned || cleaned === "-") return 0;

  const negative = cleaned.startsWith("-");
  const [whole = "0", fraction = ""] = cleaned.replace("-", "").split(".");
  const cents = Number(whole) * CENTS_PER_UNIT + Number(fraction.padEnd(2, "0").slice(0, 2));

  return Number.isFinite(cents) ? (negative ? -cents : cents) : 0;
}

export function fromCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(Math.round(cents));

  return `${sign}${Math.floor(absolute / CENTS_PER_UNIT)}.${String(
    absolute % CENTS_PER_UNIT,
  ).padStart(2, "0")}`;
}

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

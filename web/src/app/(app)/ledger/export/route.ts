import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale } from "@/i18n/config";
import { ledgerApi } from "@/lib/api";

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/**
 * The auxiliary book, proxied.
 *
 * Same reason as the exógena download: a link straight to the API would need
 * the token in the browser, and the whole point of the httpOnly cookie is that
 * it is never there.
 *
 * The filters ride in the query string, so the button is a plain link carrying
 * whatever the screen is currently showing — no fetch, no blob, no click
 * handler that has to know how to save a file.
 */
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const stored = (await cookies()).get(LOCALE_COOKIE)?.value;

  const upstream = await ledgerApi.book({
    date_from: params.get("date_from") ?? undefined,
    date_to: params.get("date_to") ?? undefined,
    account_code: params.get("account") ?? undefined,
    third_party_id: Number(params.get("third_party")) || undefined,
    // The headings follow the language the app is being read in, not the
    // server's default.
    locale: isLocale(stored) ? stored : DEFAULT_LOCALE,
  });

  if (!upstream.ok) {
    return new NextResponse(await upstream.text(), { status: upstream.status });
  }

  return new NextResponse(upstream.body, {
    headers: {
      "Content-Type": XLSX,
      "Content-Disposition":
        upstream.headers.get("content-disposition") ??
        'attachment; filename="libro-auxiliar.xlsx"',
    },
  });
}

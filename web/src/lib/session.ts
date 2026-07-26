import "server-only";

import { cookies, headers } from "next/headers";

/**
 * The access token lives in an httpOnly cookie: JavaScript cannot read it, so
 * an XSS bug cannot exfiltrate it. Only the server attaches it to API calls.
 */
export const SESSION_COOKIE = "session";

export async function readToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

export async function startSession(token: string, maxAge: number): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: await isHttps(),
    path: "/",
    maxAge,
  });
}

export async function endSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

/**
 * Whether this request arrived over TLS.
 *
 * Deliberately not `NODE_ENV === "production"`: a production build served over
 * plain HTTP would mark the cookie `Secure`, the browser would silently drop
 * it, and every write would come back unauthenticated — while the server, which
 * sees its own cookie jar within the same request, still looks signed in.
 *
 * `x-forwarded-proto` is what a reverse proxy sets, so this stays correct once
 * TLS terminates upstream.
 */
async function isHttps(): Promise<boolean> {
  const forwarded = (await headers()).get("x-forwarded-proto");
  return forwarded?.split(",")[0].trim() === "https";
}

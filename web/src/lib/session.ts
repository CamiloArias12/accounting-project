import "server-only";

import { cookies, headers } from "next/headers";

// The access token lives in an httpOnly cookie: JavaScript cannot read it, so an XSS bug cannot exfiltrate it.
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

async function isHttps(): Promise<boolean> {
  const forwarded = (await headers()).get("x-forwarded-proto");
  return forwarded?.split(",")[0].trim() === "https";
}

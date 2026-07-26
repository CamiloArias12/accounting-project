import { cookies } from "next/headers";

import { Sidebar } from "@/components/Sidebar";
import { ApiError, authApi } from "@/lib/api";
import { readToken } from "@/lib/session";
import { DEFAULT_THEME, THEME_COOKIE, isTheme } from "@/lib/theme";

/** The signed-in shell: everything reachable from the sidebar. */
export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const stored = (await cookies()).get(THEME_COOKIE)?.value;
  const theme = isTheme(stored) ? stored : DEFAULT_THEME;

  return (
    <>
      <Sidebar initialTheme={theme} userEmail={await currentUserEmail()} />
      <div className="lg:pl-60">{children}</div>
    </>
  );
}

/** Resolves the signed-in user, treating an expired token as signed out. */
async function currentUserEmail(): Promise<string | null> {
  if (!(await readToken())) return null;

  try {
    return (await authApi.me()).email;
  } catch (caught) {
    // A stale or revoked token must not break every page.
    if (caught instanceof ApiError) return null;
    throw caught;
  }
}

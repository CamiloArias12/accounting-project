import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { Toaster } from "@/components/ui/sonner";
import { ApiError, authApi } from "@/lib/api";
import { readToken } from "@/lib/session";
import { DEFAULT_THEME, THEME_COOKIE, isTheme } from "@/lib/theme";

// The signed-in shell.
export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const email = await currentUserEmail();
  if (email === null) redirect("/login");

  const stored = (await cookies()).get(THEME_COOKIE)?.value;
  const theme = isTheme(stored) ? stored : DEFAULT_THEME;

  return (
    <>
      <Sidebar initialTheme={theme} userEmail={email} />
      <div className="lg:pl-64">{children}</div>
      <Toaster position="bottom-right" />
    </>
  );
}

async function currentUserEmail(): Promise<string | null> {
  if (!(await readToken())) return null;

  try {
    return (await authApi.me()).email;
  } catch (caught) {
    if (caught instanceof ApiError) return null;
    throw caught;
  }
}

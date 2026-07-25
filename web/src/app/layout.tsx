import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import { Inter } from "next/font/google";
import { cookies } from "next/headers";

import { Sidebar } from "@/components/Sidebar";
import { ThemeScript } from "@/components/ThemeScript";
import { ApiError, authApi } from "@/lib/api";
import { readToken } from "@/lib/session";
import { DEFAULT_THEME, THEME_COOKIE, isTheme } from "@/lib/theme";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Accounting Project",
  description: "Accounting platform",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const stored = (await cookies()).get(THEME_COOKIE)?.value;
  const theme = isTheme(stored) ? stored : DEFAULT_THEME;
  const userEmail = await currentUserEmail();

  return (
    // suppressHydrationWarning: ThemeScript writes `data-theme` before React
    // hydrates, so the server markup deliberately differs on this attribute.
    <html lang={locale} suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        <NextIntlClientProvider>
          <Sidebar initialTheme={theme} userEmail={userEmail} />
          <div className="lg:pl-60">{children}</div>
        </NextIntlClientProvider>
      </body>
    </html>
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

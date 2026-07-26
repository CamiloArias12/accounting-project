import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import { Inter } from "next/font/google";

import { ThemeScript } from "@/components/ThemeScript";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Accounting Project",
  description: "Accounting platform",
};

/**
 * Only what every page needs: the document, the theme and the translations.
 *
 * The sidebar lives in the `(app)` group instead, so signing in is a page of
 * its own rather than a form framed by navigation the visitor cannot use yet.
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();

  return (
    // suppressHydrationWarning: ThemeScript writes `data-theme` before React
    // hydrates, so the server markup deliberately differs on this attribute.
    <html lang={locale} suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}

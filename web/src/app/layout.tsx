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
    //
    // The font class belongs on <html>, not <body>. Tailwind resolves
    // `--font-sans` at `:root`, and a custom property that references one
    // declared further down the tree computes to nothing — which makes
    // `font-family: var(--font-sans)` invalid and drops the whole app back to
    // the browser's default serif.
    <html
      lang={locale}
      className={`${inter.variable} font-sans antialiased`}
      suppressHydrationWarning
    >
      <head>
        <ThemeScript />
      </head>
      <body>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}

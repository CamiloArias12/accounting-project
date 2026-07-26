import { cookies } from "next/headers";

import { LocaleToggle } from "@/components/LocaleToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import { DEFAULT_THEME, THEME_COOKIE, isTheme } from "@/lib/theme";

/**
 * The signed-out shell: no navigation, since none of it is reachable yet.
 *
 * The preference toggles stay, or someone landing here in the wrong language
 * or an unreadable theme would have no way out.
 */
export default async function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const stored = (await cookies()).get(THEME_COOKIE)?.value;
  const theme = isTheme(stored) ? stored : DEFAULT_THEME;

  return (
    <>
      <div className="fixed right-4 top-4 flex gap-2">
        <ThemeToggle initialTheme={theme} />
        <LocaleToggle />
      </div>
      {children}
    </>
  );
}

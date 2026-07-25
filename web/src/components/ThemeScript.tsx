import { THEME_COOKIE } from "@/lib/theme";

/**
 * Resolves the theme before the first paint.
 *
 * The server knows the cookie but not the OS preference, so "system" can only
 * be settled in the browser. Doing it in a blocking inline script avoids the
 * flash of the wrong theme that a `useEffect` would cause.
 */
export function ThemeScript() {
  const script = `
(function () {
  try {
    var cookie = document.cookie.match(/(?:^|; )${THEME_COOKIE}=([^;]*)/);
    var choice = cookie ? decodeURIComponent(cookie[1]) : 'system';
    var dark = choice === 'dark' ||
      (choice !== 'light' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  } catch (e) {
    document.documentElement.dataset.theme = 'light';
  }
})();`.trim();

  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}

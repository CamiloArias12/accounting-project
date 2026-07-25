import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Bundles only what production needs; used by the Dockerfile.
  output: "standalone",

  // The dev server rejects cross-origin requests, which silently breaks
  // hydration when the app is opened from anything other than localhost — a
  // browser in another container, or a phone on the same network. Production
  // is unaffected.
  allowedDevOrigins: ["host.docker.internal", "*.local"],
};

export default withNextIntl(nextConfig);

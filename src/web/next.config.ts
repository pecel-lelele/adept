import path from "node:path";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // src/web is its own pnpm project; pin the root so a stray lockfile higher up is ignored.
  turbopack: { root: path.resolve(process.cwd()) },
};

export default withNextIntl(nextConfig);

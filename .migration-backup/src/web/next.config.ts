import path from "node:path";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // src/web is its own pnpm project; pin the root so a stray lockfile higher up is ignored.
  turbopack: { root: path.resolve(process.cwd()) },
  // CV uploads go through a Server Action (features/profile/actions.ts) and may be up to
  // 5 MB (the API's MAX_UPLOAD_BYTES); the default 1 MB action body limit would reject them.
  experimental: { serverActions: { bodySizeLimit: "6mb" } },
  // The dev-only Next.js badge sat on the sidebar language switch (bottom left) and on the
  // mobile tab bar's "More" (bottom right), intercepting clicks. Build errors still show.
  devIndicators: false,
};

export default withNextIntl(nextConfig);

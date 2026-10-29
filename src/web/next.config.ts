import path from "node:path";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

const nextConfig: NextConfig = {
  async headers() {
    const development = process.env.NODE_ENV === "development";
    // Next hydration and the existing JSX style attributes need inline execution/styles.
    // three.js is bundled locally; production does not need eval or external script hosts.
    const csp = [
      "default-src 'self'",
      `script-src 'self' 'unsafe-inline'${development ? " 'unsafe-eval'" : ""}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self'",
      `connect-src 'self'${development ? " ws: wss:" : ""}`,
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
    ].join("; ");
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: csp },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
      ],
    }];
  },
  output: "standalone",
  outputFileTracingRoot: path.resolve(process.cwd(), "../.."),
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    ...(process.env.REPLIT_DEV_DOMAIN ? [process.env.REPLIT_DEV_DOMAIN] : []),
    ...(process.env.REPLIT_DOMAINS ?? "").split(",").filter(Boolean),
  ],
  reactStrictMode: true,
  // Resolve workspace dependencies from the same root used by standalone tracing.
  turbopack: { root: path.resolve(process.cwd(), "../..") },
  // CV uploads go through a Server Action (features/profile/actions.ts) and may be up to
  // 5 MB (the API's MAX_UPLOAD_BYTES); the default 1 MB action body limit would reject them.
  experimental: { serverActions: { bodySizeLimit: "6mb" } },
  // The dev-only Next.js badge sat on the sidebar language switch (bottom left) and on the
  // mobile tab bar's "More" (bottom right), intercepting clicks. Build errors still show.
  devIndicators: false,
};

export default withNextIntl(nextConfig);

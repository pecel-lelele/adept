# Production web image (Next.js standalone). Build from the repository root:
#   docker build -f src/docker/web.Dockerfile .
# The pnpm workspace lockfile lives at the root, so the install uses the root manifests.
FROM node:24-alpine AS build
WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY scripts/require-pnpm.mjs scripts/require-pnpm.mjs
COPY src/web/package.json src/web/package.json
RUN pnpm install --frozen-lockfile
COPY src/web/ src/web/
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @workspace/adept build

FROM node:24-alpine AS runtime
WORKDIR /workspace
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000 NEXT_TELEMETRY_DISABLED=1
# outputFileTracingRoot is the repository root, so the server sits at src/web/server.js;
# prepare-standalone.mjs has already copied .next/static and public next to it.
COPY --from=build --chown=node:node /workspace/src/web/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "src/web/server.js"]

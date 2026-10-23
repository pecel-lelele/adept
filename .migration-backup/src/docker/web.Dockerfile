FROM node:22-alpine AS build
WORKDIR /workspace/src/web
RUN corepack enable
COPY src/web/package.json src/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY src/web/ ./
RUN pnpm build
FROM node:22-alpine AS runtime
WORKDIR /workspace/src/web
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /workspace/src/web/.next/standalone ./
COPY --from=build --chown=node:node /workspace/src/web/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]


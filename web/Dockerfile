# syntax=docker/dockerfile:1

FROM node:22-alpine AS base
WORKDIR /app


# --- deps: capa cacheable, solo se reconstruye si cambia el lockfile ---
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci


# --- dev: hot reload, el código llega por bind mount desde compose ---
FROM base AS dev
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]


# --- builder ---
FROM base AS builder
# NEXT_PUBLIC_* se inyecta en el bundle del navegador al construir, no en
# runtime: por eso llega como build arg y no como variable del contenedor.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build


# --- prod: solo el output standalone, usuario sin privilegios ---
FROM base AS prod
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -g 1001 nodejs && adduser -S -u 1001 -G nodejs nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]

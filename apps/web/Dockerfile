# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:24-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_BRAND_NAME_AR=قمرة
ARG NEXT_PUBLIC_BRAND_NAME_EN=Qamra
ARG NEXT_PUBLIC_BRAND_DOMAIN=qamra.app
ARG NEXT_PUBLIC_GOOGLE_LOGIN=0
ENV NEXT_PUBLIC_BRAND_NAME_AR=$NEXT_PUBLIC_BRAND_NAME_AR NEXT_PUBLIC_BRAND_NAME_EN=$NEXT_PUBLIC_BRAND_NAME_EN \
    NEXT_PUBLIC_BRAND_DOMAIN=$NEXT_PUBLIC_BRAND_DOMAIN NEXT_PUBLIC_GOOGLE_LOGIN=$NEXT_PUBLIC_GOOGLE_LOGIN
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S qamra && adduser -S -G qamra qamra
COPY --from=build --chown=qamra:qamra /app/.next/standalone ./
COPY --from=build --chown=qamra:qamra /app/.next/static ./.next/static
COPY --from=build --chown=qamra:qamra /app/public ./public
USER qamra
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -qO- http://127.0.0.1:3000/ar >/dev/null || exit 1
CMD ["node", "server.js"]

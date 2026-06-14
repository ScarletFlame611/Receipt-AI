# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Frontend (React + Vite) — multi-stage: сборка статики, раздача через nginx.
# nginx также проксирует API-запросы на backend (см. nginx.conf), поэтому
# фронт и бэк живут на одном origin и CORS в проде не нужен.
# ---------------------------------------------------------------------------

# --- Stage 1: сборка статики ---
FROM node:20-alpine AS build
WORKDIR /app

# Зависимости отдельным слоем для кеша. npm ci — по lock-файлу, воспроизводимо.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Stage 2: раздача через nginx ---
FROM nginx:1.27-alpine AS runtime

# SPA-конфиг с проксированием API на сервис backend.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Собранная статика Vite (dist/).
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]

# syntax=docker/dockerfile:1.7
# Frontend: Vite dev server in development, static build served by nginx in prod.

# ---------- base ----------
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---------- dev runtime ----------
FROM deps AS dev
WORKDIR /app
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---------- prod build ----------
FROM deps AS build
WORKDIR /app
COPY . .
RUN npm run build

# ---------- prod runtime ----------
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

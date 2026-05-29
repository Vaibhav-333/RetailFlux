FROM node:20-alpine AS base
WORKDIR /app

# ─── Development stage ─────────────────────────────────────────────────────
FROM base AS development
COPY package.json .
RUN npm install
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ─── Build stage ───────────────────────────────────────────────────────────
FROM base AS build
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# ─── Production stage (serve static) ──────────────────────────────────────
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

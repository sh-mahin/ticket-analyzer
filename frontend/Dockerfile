# ---------- build stage ----------
FROM node:20-alpine AS build

WORKDIR /app

# Build-time env: compiled into the bundle. In Phase 3 we set this to "/api"
# and route /api through nginx to the backend container.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json ./
# If you add a lockfile, copy it too and use `npm ci` for reproducibility.
RUN npm install --no-audit --no-fund

COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

# ---------- runtime stage ----------
FROM nginx:alpine

# Replace default site with our config (serves dist/ on :80).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

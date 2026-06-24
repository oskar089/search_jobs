# =============================================================================
#  Search Jobs Frontend - Dockerfile (multi-stage)
#  Stage 1: Build with Node     Stage 2: Serve with nginx
# =============================================================================

# ---- Stage 1: Build --------------------------------------------------------
FROM node:22-slim AS build

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve --------------------------------------------------------
FROM nginx:alpine

# Copy built assets from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config (SPA fallback, caching, gzip)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

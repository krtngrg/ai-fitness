# ─── Stage 1: deps ────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# ─── Stage 2: development ─────────────────────────────────────────────────────
FROM deps AS development

COPY . .

EXPOSE 5173

# Vite dev server — host 0.0.0.0 so Docker port mapping works
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# ─── Stage 3: builder ─────────────────────────────────────────────────────────
FROM deps AS builder

COPY . .

# Build args passed at build time
ARG VITE_API_URL=http://localhost:8000/api
ARG VITE_AI_SERVICE_URL=http://localhost:9001
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AI_SERVICE_URL=$VITE_AI_SERVICE_URL

RUN npm run build

# ─── Stage 4: production (Nginx) ──────────────────────────────────────────────
FROM nginx:1.27-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ── Stage 1: Build Next.js frontend ──
FROM node:20-alpine AS frontend-build
WORKDIR /app/backend_visualizer
COPY backend_visualizer/package.json backend_visualizer/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install
COPY backend_visualizer/ ./
ENV NEXT_PUBLIC_API_BASE_URL=""
RUN npx next build --webpack

# ── Stage 2: Final runtime ──
FROM python:3.12-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm supervisor curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY intelligence/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy Python source
COPY intelligence/ intelligence/
COPY notes_streamer/ notes_streamer/
COPY scripts/ scripts/

# Copy wiki skeleton (will be overridden by volume mount if data exists)
COPY wiki/ wiki/

# Create data dir
RUN mkdir -p data

# Copy built frontend
COPY --from=frontend-build /app/backend_visualizer/.next backend_visualizer/.next
COPY --from=frontend-build /app/backend_visualizer/node_modules backend_visualizer/node_modules
COPY --from=frontend-build /app/backend_visualizer/package.json backend_visualizer/package.json

# Supervisor config to run all processes
COPY deploy/supervisord.conf /etc/supervisor/conf.d/monty.conf

# Entrypoint script
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000 3200

ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/monty.conf"]

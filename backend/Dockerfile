# =============================================================================
#  Search Jobs Backend — Multi-stage Dockerfile
#  Stage 1 (builder):   pip install + playwright install chromium
#  Stage 2 (runtime):   python:3.12-slim, COPY --from=builder
# =============================================================================

# ---- Stage 1: Builder -------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# System dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers (Chromium only)
RUN playwright install chromium && \
    rm -rf /root/.cache/ms-playwright/chromium-*/browsers 2>/dev/null; \
    true

# ---- Stage 2: Runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system dependencies (postgresql-client for pg_isready)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages + Playwright from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Application code
COPY . .

# Create uploads directory (persisted via named volume)
RUN mkdir -p /app/uploads/cv

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

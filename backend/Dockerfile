# =============================================================================
#  Search Jobs Backend - Dockerfile
#  FastAPI + Celery + Playwright
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# ---------------------------------------------------------------------------
# System dependencies
#   - postgresql-client  → pg_isready for health checks
#   - Playwright deps    → headless Chromium for LinkedIn scraping
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
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

# ---------------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Playwright browsers (Chromium only — keeps image size manageable)
# ---------------------------------------------------------------------------
RUN playwright install chromium && \
    rm -rf /root/.cache/ms-playwright/chromium-*/browsers 2>/dev/null; \
    true

# ---------------------------------------------------------------------------
# Application code
# ---------------------------------------------------------------------------
COPY . .

# Create uploads directory (persisted via named volume)
RUN mkdir -p /app/uploads/cv

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

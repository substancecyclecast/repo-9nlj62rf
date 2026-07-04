# ── Stage 1: Frontend build ──────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python base ────────────────────────────────────
FROM python:3.14-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev poppler-utils tesseract-ocr tesseract-ocr-rus \
    fontconfig fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
 && rm -rf /var/lib/apt/lists/*

# ── Stage 3: Python deps ────────────────────────────────────
FROM base AS deps
COPY pyproject.toml requirements.lock ./
COPY src/ /app/src/
RUN pip install --upgrade pip \
 && pip install -r requirements.lock \
 && pip install -e . --no-deps

# ── Stage 4: Runtime ────────────────────────────────────────
FROM deps AS runtime
COPY . /app
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ARG BUILD_PROD=0
RUN if [ "$BUILD_PROD" = "1" ]; then pip install .[prod] && python -m playwright install --with-deps chromium; fi

EXPOSE 8000 8501
CMD ["uvicorn", "snabagent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

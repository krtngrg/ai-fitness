# ─── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# System deps needed by OpenCV (headless) and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: development ─────────────────────────────────────────────────────
FROM base AS development

# Copy source (will be overridden by volume mount in dev)
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ─── Stage 3: production ──────────────────────────────────────────────────────
FROM base AS production

# Install gunicorn for production WSGI
RUN pip install --no-cache-dir gunicorn==23.0.0

COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input --settings=backend.settings || true

EXPOSE 8000

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]

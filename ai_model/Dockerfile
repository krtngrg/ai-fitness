# ─── Stage 1: base ────────────────────────────────────────────────────────────
# OpenCV requires specific system libraries. Using slim + manual install
# keeps the image as small as possible.
FROM python:3.12-slim AS base

WORKDIR /app

# OpenCV system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1-mesa-glx \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements_ai.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements_ai.txt

# ─── Stage 2: development ─────────────────────────────────────────────────────
FROM base AS development

COPY . .

EXPOSE 9001

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "9001", "--reload"]

# ─── Stage 3: production ──────────────────────────────────────────────────────
FROM base AS production

COPY . .

EXPOSE 9001

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "9001", "--workers", "2"]

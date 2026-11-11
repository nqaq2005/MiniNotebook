# =====================================================================
# Dockerfile for MiniNotebook Application
# =====================================================================
FROM python:3.11-slim-bookworm

# Python environment hardening
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Install system runtime libraries needed by PyMuPDF, RapidOCR (OpenCV/ONNX), and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Cache dependencies layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-create data directories with correct permissions
RUN mkdir -p /app/data/raw_pdfs \
             /app/data/parsed_md \
             /app/data/vector_db \
             /app/data/models_cache \
             /app/data/citation_graph \
             /app/data/qdrant_server_storage && \
    chown -R appuser:appgroup /app

# Copy application codebase
COPY --chown=appuser:appgroup . /app

USER appuser

EXPOSE 8000

# Container liveness check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Launch production ASGI server
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]

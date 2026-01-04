# Mixamo Blend Pipeline - Production Dockerfile
# Multi-stage build for optimized production image
#
# Author: Ted Iro
# Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
# Date: January 4, 2026
#
# Build stages:
#   1. builder - Install dependencies and compile Python packages
#   2. runtime - Minimal production image with only runtime dependencies
#
# Usage:
#   docker build -t mixamo-blend-pipeline:latest .
#   docker run -e GCS_BUCKET=my-bucket mixamo-blend-pipeline:latest

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set build-time metadata
LABEL stage=builder
LABEL maintainer="Ted Iro <ted@rydlrcloudservices.com>"
LABEL org.opencontainers.image.source="https://github.com/rydlrcs/mixamo-blend-pipeline"

# Install build dependencies required for compiling Python packages
# gcc: C compiler for native extensions
# python3-dev: Python headers for building extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        && \
    rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /build

# Copy only requirements first for better layer caching
# This layer will only rebuild if requirements.txt changes
COPY requirements.txt .

# Create virtual environment and install dependencies
# Using --no-cache-dir to reduce image size
# Using --compile to generate bytecode for faster startup
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir --compile -r requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Set production metadata
LABEL maintainer="Ted Iro <ted@rydlrcloudservices.com>"
LABEL org.opencontainers.image.title="Mixamo Blend Pipeline"
LABEL org.opencontainers.image.description="Production pipeline for Mixamo animation blending"
LABEL org.opencontainers.image.source="https://github.com/rydlrcs/mixamo-blend-pipeline"
LABEL org.opencontainers.image.vendor="Rydlr Cloud Services Ltd"
LABEL org.opencontainers.image.version="0.1.0"

# Install runtime dependencies only
# ca-certificates: Required for HTTPS connections to GCS
# curl: Required for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# Running as non-root is a security best practice
# UID 1000 is standard for first user in most Linux distributions
RUN groupadd --gid 1000 pipeline && \
    useradd --uid 1000 --gid pipeline --shell /bin/bash --create-home pipeline

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
# This includes all installed Python packages
COPY --from=builder /opt/venv /opt/venv

# Copy application code
# Ownership set to pipeline user for security
COPY --chown=pipeline:pipeline src/ ./src/
COPY --chown=pipeline:pipeline scripts/ ./scripts/
COPY --chown=pipeline:pipeline config/ ./config/
COPY --chown=pipeline:pipeline pyproject.toml .
COPY --chown=pipeline:pipeline README.md .

# Create directories for data with appropriate permissions
# These directories will be used for temporary file storage
RUN mkdir -p /app/data/seed /app/data/blend /app/data/output /app/logs && \
    chown -R pipeline:pipeline /app/data /app/logs

# Set environment variables
# PATH: Include virtual environment binaries
# PYTHONUNBUFFERED: Ensure Python output is sent straight to terminal
# PYTHONDONTWRITEBYTECODE: Don't create .pyc files (cleaner container)
# PYTHONPATH: Add /app to Python import path
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
# All subsequent commands and container runtime will use this user
USER pipeline

# Expose health check port (if implementing HTTP health endpoint)
EXPOSE 8080

# Health check configuration
# Checks that Python can import the main modules
# Runs every 30 seconds with 3 second timeout
# Container is unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import src.blender, src.uploader, src.downloader; print('OK')" || exit 1

# Default command: Show help
# Override this in docker-compose or kubernetes deployment
CMD ["python", "-m", "src.utils.logging"]

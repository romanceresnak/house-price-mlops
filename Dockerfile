# ============================================================================
# Multi-stage Dockerfile pre SageMaker Training Container
# ============================================================================

FROM python:3.11-slim as base

# Metadata
LABEL maintainer="Roman Ceresnak"
LABEL description="House Price MLOps - SageMaker Training Container"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================================================
# Builder stage - install dependencies
# ============================================================================

FROM base as builder

WORKDIR /build

# System dependencies pre build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Runtime stage - minimal image
# ============================================================================

FROM base as runtime

# System dependencies (runtime only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# SageMaker specific directories
# /opt/ml/input/data/training - training data
# /opt/ml/model - model output
# /opt/ml/code - source code (default working directory)
WORKDIR /opt/ml/code

# Copy source code
COPY src/ ./src/

# Set PYTHONPATH
ENV PYTHONPATH=/opt/ml/code

# SageMaker uses this as entry point
# Can be overridden via hyperparameters
ENV SAGEMAKER_PROGRAM=src/train/train.py

# Default command (can be overridden)
# SageMaker will run: python $SAGEMAKER_PROGRAM [args]
CMD ["python", "src/train/train.py"]

# ============================================================================
# Health check (optional, pre local testing)
# ============================================================================

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import xgboost, mlflow, sklearn; print('OK')" || exit 1

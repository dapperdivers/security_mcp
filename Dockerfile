# Multi-stage production Dockerfile with security best practices
# Build stage - for downloading and preparing dependencies
FROM python:3.11-slim AS builder

# Build arguments
ARG TARGETARCH=amd64

# Install build dependencies and Bearer CLI from official APT repository
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        apt-transport-https \
        gnupg \
    && update-ca-certificates && \
    echo "deb [trusted=yes] https://apt.fury.io/bearer/ /" | tee -a /etc/apt/sources.list.d/fury.list && \
    apt-get update && \
    apt-get install -y bearer && \
    # Copy bearer to /tmp for builder stage
    cp $(which bearer) /tmp/bearer && \
    bearer version && \
    # Clean up APT cache to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create Python virtual environment and install dependencies
WORKDIR /app
COPY requirements.txt pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage - minimal final image
FROM python:3.11-slim AS runtime

# Runtime build arguments for metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.1

# Install minimal runtime dependencies including git for Bearer scanning
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Bearer CLI from builder stage
COPY --from=builder /tmp/bearer /usr/local/bin/bearer

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user with minimal privileges
RUN groupadd -r -g 1000 mcpuser && \
    useradd -r -g mcpuser -u 1000 -m -s /sbin/nologin mcpuser

# Create necessary directories with proper ownership
RUN mkdir -p /app /workspace /config && \
    chown -R mcpuser:mcpuser /app /workspace /config

# Set up application directory
WORKDIR /app

# Copy application source code with proper ownership
COPY --chown=mcpuser:mcpuser bearer_mcp_main.py ./
COPY --chown=mcpuser:mcpuser bearer_mcp/ ./bearer_mcp/

# Environment variables for security and operation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH=/opt/venv/bin:$PATH \
    MCP_WORKING_DIRECTORY=/workspace \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Switch to non-root user
USER mcpuser

# Health check to verify both Python server and Bearer CLI work
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import bearer_mcp; print('OK')" && bearer version > /dev/null || exit 1

# Expose port for SSE transport (non-privileged port)
EXPOSE 8000

# Use exec form for proper signal handling
CMD ["python", "bearer_mcp_main.py"]

# Read-only root filesystem support - create necessary directories
VOLUME ["/workspace", "/tmp"]

# Security and build metadata labels
LABEL maintainer="Bearer MCP Server Team" \
      org.opencontainers.image.title="Bearer MCP Server" \
      org.opencontainers.image.description="MCP server that wraps the Bearer CLI security scanning tool with auto-updated Bearer version" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Bearer" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Bearer/bearer-mcp-server" \
      bearer.version="1.0.1" \
      security.non-root="true" \
      security.readonly-rootfs="supported"
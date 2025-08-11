# Production Dockerfile with all dependencies
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Download and install Bearer CLI with retry logic
RUN curl -L --retry 5 --retry-delay 10 --max-time 300 \
    -o /tmp/bearer.tar.gz \
    "https://github.com/Bearer/bearer/releases/download/v1.50.0/bearer_1.50.0_linux_amd64.tar.gz" \
    && tar -xzf /tmp/bearer.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/bearer \
    && rm /tmp/bearer.tar.gz

# Set up application directory
WORKDIR /app

# Copy application files
COPY pyproject.toml bearer_mcp_server.py ./

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir fastapi>=0.104.0 uvicorn>=0.24.0

# Create workspace directory
RUN mkdir -p /workspace /config

# Create non-root user for security
RUN useradd -m -s /bin/bash mcpuser && \
    chown -R mcpuser:mcpuser /app /workspace /config

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_WORKING_DIRECTORY=/workspace
ENV PYTHONPATH=/app

# Switch to non-root user
USER mcpuser

# Health check to verify Bearer CLI works
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD bearer version > /dev/null || exit 1

# Expose port for SSE transport
EXPOSE 8000

# Run the MCP server
CMD ["python", "bearer_mcp_server.py"]

# Volume for scanning workspace
VOLUME ["/workspace"]

# Metadata
LABEL maintainer="Bearer MCP Server" \
      description="MCP server that wraps the Bearer CLI security scanning tool" \
      version="1.0.1" \
      bearer.version="1.50.0"
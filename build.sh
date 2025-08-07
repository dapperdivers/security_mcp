#!/bin/bash
# Build script with local caching

echo "Bearer MCP Server Docker Build Script"
echo "======================================"

# Option 1: Build minimal version (fastest)
echo "1. Building minimal version (no dependencies)..."
docker build -f Dockerfile.minimal -t bearer-mcp:minimal .

if [ $? -eq 0 ]; then
    echo "✓ Minimal build successful!"
    echo ""
    echo "To use the minimal version:"
    echo "  1. Install MCP dependencies on host: pip install mcp>=1.2.0"
    echo "  2. Download Bearer CLI: https://github.com/Bearer/bearer/releases"
    echo "  3. Run: docker run -v \$(pwd):/workspace bearer-mcp:minimal"
else
    echo "✗ Minimal build failed"
fi

echo ""
echo "======================================"
echo "For production use with slow network:"
echo ""
echo "Option A: Use pre-built image from Docker Hub (when available)"
echo "  docker pull bearer/mcp-server"
echo ""
echo "Option B: Build offline with cached dependencies:"
echo "  1. Download Python packages: pip download mcp>=1.2.0 -d ./pip-cache"
echo "  2. Download Bearer: wget https://github.com/Bearer/bearer/releases/download/v1.50.0/bearer_1.50.0_linux_amd64.tar.gz"
echo "  3. Build with local cache: docker build -f Dockerfile.cached -t bearer-mcp ."
echo ""
echo "Option C: Use the minimal image and mount dependencies:"
echo "  docker run -v /usr/local/bin/bearer:/usr/local/bin/bearer:ro bearer-mcp:minimal"
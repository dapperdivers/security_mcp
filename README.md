# Bearer MCP Server

A Model Context Protocol (MCP) server that wraps the Bearer CLI security scanning tool, providing AI assistants with the ability to perform static application security testing (SAST) on codebases.

## Features

- **Security Scanning**: Run Bearer security scans on directories and files
- **Multiple Output Formats**: Support for JSON, YAML, SARIF, and HTML output formats
- **Rule Management**: List and filter security rules by language and category
- **Configuration Management**: Initialize Bearer configuration files in projects
- **Docker Support**: Containerized deployment with Bearer CLI pre-installed
- **Working Directory Context**: Proper handling of working directories from MCP configuration

## Bearer CLI Overview

Bearer is a static application security testing (SAST) tool that scans source code for security vulnerabilities and sensitive data leaks. It supports multiple programming languages including Go, Java, JavaScript, TypeScript, PHP, Python, and Ruby.

## Installation

### Prerequisites

- Python 3.10 or higher
- Bearer CLI (installed automatically in Docker version)

### Option 1: Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/bearer-mcp-server.git
   cd bearer-mcp-server
   ```

2. **Install Bearer CLI**:
   ```bash
   # macOS/Linux
   curl -sfL https://raw.githubusercontent.com/Bearer/bearer/main/contrib/install.sh | sh
   
   # Or using Homebrew (macOS)
   brew install bearer/tap/bearer
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the MCP Server**:
   ```bash
   pip install -e .
   ```

### Option 2: Docker Installation (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/bearer-mcp-server.git
   cd bearer-mcp-server
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t bearer-mcp-server .
   ```

3. **Or use Docker Compose**:
   ```bash
   docker-compose build
   ```


## Configuration

### MCP Client Configuration

Add the server to your MCP client configuration:

**For Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "bearer-security": {
      "command": "python",
      "args": ["/path/to/security_mcp/bearer_mcp_server.py"],
      "env": {
        "MCP_WORKING_DIRECTORY": "/path/to/your/project"
      }
    }
  }
}
```

**For generic MCP clients** (`mcp.json`):
```json
{
  "mcpServers": {
    "bearer-security": {
      "command": "python",
      "args": ["/path/to/security_mcp/bearer_mcp_server.py"],
      "env": {
        "MCP_WORKING_DIRECTORY": "/path/to/your/project"
      }
    }
  }
}
```

### Docker Configuration

**Using Docker Compose**:
```yaml
services:
  bearer-mcp-server:
    build: .
    volumes:
      - ./your-project:/workspace:ro
    environment:
      - MCP_WORKING_DIRECTORY=/workspace
```

**Using Docker directly**:
```bash
docker run -it --rm \
  -v /path/to/your/project:/workspace:ro \
  -e MCP_WORKING_DIRECTORY=/workspace \
  bearer-mcp-server
```

## Available Tools

### 1. `bearer_scan`

Run Bearer security scan on a directory or file.

**Parameters**:
- `path` (required): Path to scan (directory or file)
- `format` (optional): Output format - `json`, `yaml`, `sarif`, `html` (default: `json`)
- `severity` (optional): Minimum severity level - `critical`, `high`, `medium`, `low`
- `rules` (optional): Comma-separated list of rule IDs to run
- `skip_rules` (optional): Comma-separated list of rule IDs to skip
- `output_file` (optional): Path to save scan results to file
- `quiet` (optional): Suppress progress output (default: `false`)

**Example**:
```json
{
  "path": "./src",
  "format": "json",
  "severity": "high",
  "quiet": false
}
```

### 2. `bearer_version`

Get Bearer CLI version information.

**Parameters**: None

### 3. `bearer_list_rules`

List available Bearer security rules.

**Parameters**:
- `language` (optional): Filter by programming language (e.g., `javascript`, `python`, `java`)
- `category` (optional): Filter by category (e.g., `security`, `privacy`)

**Example**:
```json
{
  "language": "javascript",
  "category": "security"
}
```

### 4. `bearer_init_config`

Initialize Bearer configuration file in a project.

**Parameters**:
- `path` (optional): Directory to create configuration in (defaults to working directory)

## Usage Examples

### Basic Security Scan

Ask your AI assistant:
```
"Scan the current project for security vulnerabilities using Bearer"
```

The assistant will use the `bearer_scan` tool with the working directory configured in your MCP setup.

### Detailed Scan with Filters

```
"Run a Bearer security scan on the ./src directory, showing only critical and high severity issues, and output the results in SARIF format"
```

### List Available Rules

```
"Show me all available Bearer security rules for JavaScript"
```

### Initialize Configuration

```
"Set up Bearer configuration for this project"
```

## Working Directory Handling

The server supports working directory context through:

1. **Environment Variable**: Set `MCP_WORKING_DIRECTORY` in your MCP configuration
2. **Relative Paths**: Relative paths in tool arguments are resolved against the working directory
3. **Docker Volumes**: Mount your project directory to `/workspace` in the container

## Error Handling

The server includes comprehensive error handling:

- **Bearer CLI Not Found**: Clear error messages when Bearer isn't installed
- **Invalid Paths**: Validation of file and directory paths
- **Command Failures**: Detailed error reporting with exit codes and stderr output
- **JSON Parsing**: Graceful handling of malformed Bearer output

## Logging

Logs are written to stderr (required for STDIO transport) and include:
- Command executions with working directories
- Error conditions and debugging information
- Bearer CLI installation status

## Security Considerations

- **Read-only Scanning**: The server only reads files for scanning
- **Path Validation**: All paths are validated and resolved safely
- **Container Security**: Docker image runs as non-root user
- **Resource Limits**: Docker Compose includes resource constraints

## Quick Start

After installation, configure your MCP client and start using Bearer security scanning:

1. **Add to your MCP client configuration** (see Configuration section)
2. **Restart your MCP client**
3. **Ask your AI assistant**: "Scan my project for security vulnerabilities with Bearer"

## Development

### Running Locally

```bash
# Install in development mode
pip install -e .

# Run the server directly
python bearer_mcp_server.py

# Run with specific working directory
MCP_WORKING_DIRECTORY=/path/to/project python bearer_mcp_server.py
```

### Testing

```bash
# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_server.py
```

### Building Docker Image

```bash
# Build the image
docker build -t bearer-mcp-server .

# Test the container
docker run --rm bearer-mcp-server bearer version
```

## Troubleshooting

### Bearer CLI Not Found

If you get "Bearer CLI not found" errors:

1. **Local Installation**: Ensure Bearer is installed and in PATH
2. **Docker**: Use the provided Docker image which includes Bearer CLI
3. **Manual Installation**: Follow the Bearer CLI installation guide

### Permission Issues

For Docker deployments:
1. Ensure proper volume mounting permissions
2. The container runs as user `mcpuser` (UID 1001)
3. Mount project directories as read-only when possible

### Path Resolution Issues

1. Check that `MCP_WORKING_DIRECTORY` is set correctly
2. Verify that relative paths are correct from the working directory
3. Use absolute paths when in doubt

## License

This MCP server is licensed under the MIT License. Bearer CLI is licensed under the Elastic License 2.0 (ELv2).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

- **Bearer CLI Issues**: https://github.com/Bearer/bearer/issues
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Server Issues**: Create an issue in this repository
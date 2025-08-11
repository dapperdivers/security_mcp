# Bearer MCP Server - Refactored Structure

## Directory Structure

```
bearer_mcp/
├── __init__.py          # Package initialization
├── __main__.py          # Main entry point
├── server.py            # Main server class
├── core/                # Core functionality
│   ├── __init__.py
│   ├── config.py        # Configuration and constants
│   └── bearer_executor.py # Bearer CLI command execution
├── tools/               # Tool-related modules
│   ├── __init__.py
│   ├── definitions.py   # MCP tool definitions
│   └── handlers.py      # Tool handler implementations
├── transport/           # Transport layers
│   ├── __init__.py
│   ├── stdio.py         # STDIO transport
│   └── sse.py           # SSE transport
└── utils/               # Utility modules
    ├── __init__.py
    └── path_utils.py    # Path validation utilities
```

## Key Improvements

### Separation of Concerns
- **Core**: Configuration, logging, and Bearer CLI execution
- **Tools**: MCP tool definitions and handler logic
- **Transport**: STDIO and SSE transport implementations
- **Utils**: Shared utilities like path validation

### Design Patterns
- **Registry Pattern**: Tool handlers are managed via a registry
- **Dependency Injection**: Handlers receive dependencies via constructor
- **Factory Pattern**: `create_server()` factory function
- **Abstract Base Classes**: Base handler classes for consistency

### Pythonic Improvements
- Type hints throughout
- F-strings for formatting
- Walrus operator for concise assignments
- Proper exception handling
- PEP 8 compliant naming and structure

## Usage

### As a Module
```python
from bearer_mcp import create_server

server = create_server()
```

### As a Script
```bash
python bearer_mcp_main.py
# or
python -m bearer_mcp
```

### Environment Variables
- `MCP_TRANSPORT`: Transport type (stdio/sse)
- `MCP_WORKING_DIRECTORY`: Working directory for scans
- `MCP_SSE_HOST`: SSE server host (default: localhost)
- `MCP_SSE_PORT`: SSE server port (default: 8000)

## Architecture Benefits

1. **Maintainability**: Clear separation makes it easy to modify specific components
2. **Testability**: Dependency injection enables easy mocking and testing
3. **Extensibility**: New tools can be added by extending base classes
4. **Readability**: Logical organization improves code discovery
5. **Reusability**: Components can be imported and used independently
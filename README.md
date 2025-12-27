# Pinecone

A bundler for multi-file PineScript development. Write modular PineScript code across multiple files and bundle them into a single TradingView-compatible script.

## Features

- **Multi-file support** - Split your PineScript code into multiple files
- **Import/Export system** - Use `// @import` and `// @export` directives
- **Automatic namespacing** - Prevents variable/function collisions between modules
- **External import deduplication** - TradingView library imports are deduplicated automatically
- **Watch mode** - Rebuild automatically when files change
- **Clipboard support** - Copy bundled output directly to clipboard

## Installation

Clone the repository and install in development mode:

```bash
git clone https://github.com/yourusername/pinecone-bundler.git
cd pinecone-bundler
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Quick Start

### 1. Create a project structure

```
my-indicator/
├── pine.config.json
└── src/
    ├── main.pine
    └── utils.pine
```

### 2. Configure your project

Create `pine.config.json` in your project root:

```json
{
  "entry": "src/main.pine",
  "output": "dist/bundle.pine"
}
```

### 3. Create your modules

**src/utils.pine** - Export functions you want to share:

```pinescript
//@version=5
// @export double, triple

double(x) =>
    x * 2

triple(x) =>
    x * 3
```

**src/main.pine** - Import and use them:

```pinescript
//@version=5
// @import { double, triple } from "./utils.pine"

indicator("My Indicator", overlay=true)

result = double(close)
plot(result)
```

### 4. Bundle your project

```bash
pinecone build
```

This creates `dist/bundle.pine` with all modules combined and properly namespaced.

## CLI Commands

```bash
# Basic build
pinecone build

# Build with custom config path
pinecone build --config path/to/pine.config.json

# Watch mode - rebuild on file changes
pinecone build --watch

# Copy output to clipboard after build
pinecone build --copy
```

## How It Works

1. **Parses** your entry file and discovers all imports
2. **Resolves** the dependency graph (with circular dependency detection)
3. **Renames** all top-level identifiers in dependency modules to prevent collisions
4. **Merges** all modules in topological order
5. **Outputs** a single TradingView-compatible PineScript file

### Namespacing Example

If `utils.pine` defines `myFunc`, it becomes `__utils__myFunc` in the bundle. Your imports are automatically updated to reference the renamed version.

## Requirements

- Python 3.10+

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

## License

MIT

# Pinecone

A bundler for multi-file PineScript development. Write modular PineScript code across multiple files and bundle them into a single TradingView-compatible script.

## Why Pinecone?

TradingView's PineScript doesn't support importing code from other files. As your indicators and strategies grow, maintaining everything in a single file becomes painful.

Pinecone solves this by letting you:

- **Split your code** into multiple files
- **Import and export** functions between files
- **Bundle everything** into a single TradingView-compatible script

## Features

- **Multi-file support** - Organize your PineScript code across multiple files
- **Import/Export system** - Use familiar `// @import` and `// @export` directives
- **Automatic namespacing** - Prevents variable/function collisions between modules
- **External import deduplication** - TradingView library imports are deduplicated automatically
- **Watch mode** - Rebuild automatically when files change
- **Clipboard support** - Copy bundled output directly to clipboard

## Quick Example

**src/utils.pine**
```pinescript
//@version=5
// @export double

double(x) =>
    x * 2
```

**src/main.pine**
```pinescript
//@version=5
// @import { double } from "./utils.pine"

indicator("My Indicator", overlay=true)
result = double(close)
plot(result)
```

**Run the bundler:**
```bash
pinecone build
```

**Output: dist/bundle.pine**
```pinescript
//@version=5
indicator("My Indicator", overlay=true)

// --- Bundled modules ---
// --- From: utils.pine ---
__utils__double(x) =>
    x * 2

// --- Main ---
result = __utils__double(close)
plot(result)
```

## Get Started

Ready to try it? Head to the [Getting Started](getting-started.md) guide.

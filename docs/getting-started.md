# Getting Started

This guide will walk you through installing Pinecone and creating your first multi-file PineScript project.

## Installation

### Prerequisites

- Python 3.10 or higher
- Git

### Install Pinecone

Clone the repository and install in development mode:

```bash
git clone https://github.com/claudianadalin/pinecone.git
cd pinecone
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

Verify the installation:

```bash
pinecone --version
```

## Create Your First Project

### 1. Set up the project structure

Create a new directory for your PineScript project:

```bash
mkdir my-indicator
cd my-indicator
```

Create the following structure:

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

| Field | Description |
|-------|-------------|
| `entry` | Path to your main PineScript file (relative to config) |
| `output` | Where to write the bundled output |

### 3. Create a utility module

Create `src/utils.pine` with some reusable functions:

```pinescript
//@version=5
// @export double, triple

double(x) =>
    x * 2

triple(x) =>
    x * 3
```

!!! note "Export Directive"
    The `// @export` comment tells Pinecone which functions should be available for import by other files.

### 4. Create your main file

Create `src/main.pine`:

```pinescript
//@version=5
// @import { double } from "./utils.pine"

indicator("My First Bundled Indicator", overlay=true)

result = double(close)
plot(result, "Doubled Close", color=color.blue)
```

!!! note "Import Directive"
    The `// @import { ... } from "..."` syntax imports specific functions from another file. The path is relative to the current file.

### 5. Bundle your project

Run the bundler:

```bash
pinecone build
```

You should see:

```
✓ Bundled 2 module(s) → dist/bundle.pine
```

### 6. Use in TradingView

1. Open `dist/bundle.pine`
2. Copy the entire contents
3. Paste into TradingView's Pine Editor
4. Click "Add to Chart"

!!! tip "Quick Copy"
    Use `pinecone build --copy` to automatically copy the output to your clipboard.

## Next Steps

- Learn about all [configuration options](configuration.md)
- Explore the [CLI commands](cli.md)
- Understand [how the bundler works](how-it-works.md)

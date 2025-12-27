# How It Works

This page explains what happens when you run `pinecone build`.

## The Bundling Pipeline

```
┌─────────────────┐
│  1. Parse       │  Read entry file and discover imports
└────────┬────────┘
         │
┌────────▼────────┐
│  2. Resolve     │  Build dependency graph, detect cycles
└────────┬────────┘
         │
┌────────▼────────┐
│  3. Rename      │  Prefix all identifiers to avoid collisions
└────────┬────────┘
         │
┌────────▼────────┐
│  4. Merge       │  Combine modules in dependency order
└────────┬────────┘
         │
┌────────▼────────┐
│  5. Output      │  Write single TradingView-compatible file
└─────────────────┘
```

## Step 1: Parse

Pinecone reads your entry file and parses:

- **PineScript AST** - Using the pynescript library
- **Export directives** - `// @export functionName`
- **Import directives** - `// @import { fn } from "./file.pine"`

## Step 2: Resolve Dependencies

Starting from the entry file, Pinecone:

1. Discovers all `// @import` directives
2. Recursively parses imported files
3. Builds a dependency graph
4. Performs topological sort (dependencies before dependents)
5. Detects circular dependencies

**Example dependency graph:**

```
main.pine
├── utils/math.pine
│   └── utils/constants.pine
└── utils/format.pine
    └── utils/math.pine (already resolved)
```

**Topological order:** constants → math → format → main

## Step 3: Rename Identifiers

To prevent naming collisions when modules are combined, Pinecone renames all top-level identifiers in dependency modules.

**Before:**
```pinescript
// utils/math.pine
double(x) => x * 2
result = 0
```

**After:**
```pinescript
__utils_math__double(x) => x * 2
__utils_math__result = 0
```

### Naming Convention

The prefix is derived from the file path:

| File Path | Prefix |
|-----------|--------|
| `src/utils.pine` | `__utils__` |
| `src/utils/math.pine` | `__utils_math__` |
| `src/indicators/rsi.pine` | `__indicators_rsi__` |

### What Gets Renamed

- ✅ Variables
- ✅ Functions
- ✅ References to renamed identifiers
- ❌ Methods (called via dot notation, no collision risk)
- ❌ Entry file identifiers (stays as-is)

## Step 4: Merge Modules

Modules are merged in topological order:

1. **Version annotation** - From entry file
2. **Indicator/Strategy declaration** - From entry file
3. **External imports** - Deduplicated TradingView library imports
4. **Dependency modules** - In topological order
5. **Entry module code** - The main script

## Step 5: Post-Processing

Before writing the output, Pinecone applies fixes for known issues:

### Generic Type Syntax Fix

The pynescript library has a bug where generic types get malformed:

```pinescript
// Before (broken)
array.new < line > 500

// After (fixed)
array.new<line>(500)
```

### Import Deduplication

If multiple modules import the same TradingView library, duplicates are removed:

```pinescript
// Multiple modules import TradingView/ta/9
// Output contains only one import at the top:
import TradingView/ta/9 as ta
```

## Example: Full Pipeline

**Input files:**

```pinescript
// src/utils.pine
//@version=5
// @export double
double(x) => x * 2
```

```pinescript
// src/main.pine
//@version=5
// @import { double } from "./utils.pine"
indicator("Test")
result = double(close)
plot(result)
```

**Output:**

```pinescript
//@version=5
indicator("Test")

// --- Bundled modules ---
// --- From: utils.pine ---
__utils__double(x) => x * 2

// --- Main ---
result = __utils__double(close)
plot(result)
```

## Performance

Pinecone is fast because it:

- Only parses files once
- Caches the dependency graph
- Uses efficient AST transformations

For most projects, bundling takes less than a second.

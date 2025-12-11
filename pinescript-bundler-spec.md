# PineScript Bundler Project Specification

## The Problem

Working with PineScript at scale is painful. TradingView treats PineScript as "code that lives in their editor" rather than "code that lives on your machine." This creates a miserable workflow:

1. You can't separate code into multiple files
2. No nested functions means no scope-based organization
3. To share code between scripts, you must publish it as a TradingView library
4. Updating a library means: edit locally → push to git → update in TradingView editor → republish library → bump version in consuming script → push that to git → update in TradingView editor → save

If you have a complex indicator that uses multiple libraries, a single change cascades into a dozen manual steps.

## The Solution

A local-first bundler that lets you write PineScript across multiple files with a module system, then compiles everything into a single TradingView-compatible output file.

```
your-project/
├── src/
│   ├── main.pine              # entry point
│   ├── indicators/
│   │   ├── rsi.pine           # // @export rsiCustom
│   │   └── macd.pine          # // @export macdCustom  
│   └── utils/
│       └── helpers.pine       # // @export formatPrice, roundTo
├── pine.config.json           # bundler config
└── dist/
    └── output.pine            # bundled, namespaced output
```

Write clean, organized code locally. Run one command. Get a single file you paste into TradingView.

---

## Technical Background

### What is an AST?

AST (Abstract Syntax Tree) is to code what the DOM is to HTML.

When a browser receives HTML, it doesn't keep it as a string. It parses it into a tree structure (the DOM) that you can manipulate programmatically:

```html
<div class="container">
  <p>Hello</p>
</div>
```

Becomes:

```
HTMLDivElement
├── className: "container"
└── children:
    └── HTMLParagraphElement
        └── textContent: "Hello"
```

An AST is the same concept for code. This PineScript:

```pine
length = input(14)
vrsi = ta.rsi(close, length)
```

Becomes:

```
Assign
├── target: Name(id='length')
└── value: Call
    ├── func: Name(id='input')
    └── args: [Constant(14)]

Assign
├── target: Name(id='vrsi')
└── value: Call
    ├── func: Attribute(value=Name('ta'), attr='rsi')
    └── args: [Name('close'), Name('length')]
```

You can walk this tree, find nodes, rename things, add code, remove code—then "unparse" it back to text.

### Parser vs Bundler (Babel vs Webpack)

**Babel** is a parser/transformer. It takes one JavaScript file, parses it to AST, lets you transform it, and outputs JavaScript. It has no concept of multiple files or imports.

**Webpack** is a bundler built on top of parsers. It:
1. Starts at an entry file
2. Uses a parser (like Babel) to get the AST
3. Walks the AST looking for `import` statements
4. Resolves those imports to actual files
5. Recursively parses those files
6. Builds a dependency graph
7. Transforms/merges all ASTs (renaming to avoid collisions)
8. Outputs bundled code

The parser is a tool. The bundler is the product that uses the tool.

### Where pynescript Fits

**pynescript** is Babel for PineScript. It:
- Parses PineScript text → AST
- Can dump AST for inspection
- Unparses AST → PineScript text

It handles the hard part (correctly parsing PineScript's weird syntax) but doesn't do anything useful on its own. It's a foundation.

**Our bundler** would be Webpack for PineScript. It uses pynescript as the parsing engine, then adds:
- Multi-file support
- Import/export syntax
- Dependency resolution
- Identifier renaming
- Merging and output

---

## Existing Tools Landscape

### pynescript (Python, LGPL-3.0)
- **What it does**: Parse/unparse PineScript using ANTLR
- **GitHub**: 79 stars, 22 forks, actively maintained (last update Dec 2025)
- **Why it matters**: Handles the hardest part of our problem
- **Limitations**: Single file only, no module system, no bundling

### pine-js (JavaScript)
- **What it does**: JavaScript parser for PineScript
- **GitHub**: 17 stars, less maintained
- **Why it matters**: Alternative if we wanted JS
- **Limitations**: Unclear modern PineScript support, smaller community

### PyneCore/PyneSys
- **What they do**: Transpile PineScript to Python to run backtests locally
- **Why they matter**: Different problem (execution vs organization)
- **Limitations**: Not relevant to our bundling use case

### VS Code Extensions
- **What they do**: Syntax highlighting, snippets
- **Limitations**: No bundling, no multi-file support

### What Doesn't Exist
Nobody has built the actual bundler workflow. The gap is: multi-file development → single bundled output.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User's Project                          │
├─────────────────────────────────────────────────────────────────┤
│  src/                                                           │
│  ├── main.pine         (entry point)                            │
│  ├── indicators/                                                │
│  │   └── rsi.pine      (// @export customRsi)                   │
│  └── utils/                                                     │
│      └── math.pine     (// @export round, clamp)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Bundler Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│  1. Read entry file                                             │
│  2. Scan for // @import directives                              │
│  3. Resolve import paths to actual files                        │
│  4. Parse each file with pynescript → AST                       │
│  5. Build dependency graph                                      │
│  6. Topologically sort (dependencies before dependents)         │
│  7. Walk each AST, rename exported identifiers with prefixes    │
│  8. Update all references to renamed identifiers                │
│  9. Merge ASTs into single tree                                 │
│  10. Unparse with pynescript → output.pine                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Output                                 │
├─────────────────────────────────────────────────────────────────┤
│  dist/output.pine                                               │
│  - Single file                                                  │
│  - All identifiers namespaced (no collisions)                   │
│  - Valid PineScript that TradingView accepts                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module System Design

### Import Syntax (Comment-Based)

Using comments means unbundled code won't break if accidentally pasted into TradingView:

```pine
// @import { customRsi } from "./indicators/rsi.pine"
// @import { round, clamp } from "./utils/math.pine"

//@version=5
indicator("My Indicator", overlay=true)

r = customRsi(close, 14)
plot(round(r, 2))
```

### Export Syntax

```pine
// @export customRsi

//@version=5

customRsi(src, len) =>
    change = ta.change(src)
    gain = ta.rma(math.max(change, 0), len)
    loss = ta.rma(-math.min(change, 0), len)
    100 - (100 / (1 + gain / loss))
```

### Bundled Output Example

Given the above files, output would look like:

```pine
//@version=5
indicator("My Indicator", overlay=true)

// --- Begin: utils/math.pine ---
__utils_math__round(val, decimals) =>
    mult = math.pow(10, decimals)
    math.round(val * mult) / mult

__utils_math__clamp(val, minVal, maxVal) =>
    math.max(minVal, math.min(maxVal, val))

// --- Begin: indicators/rsi.pine ---
__indicators_rsi__customRsi(src, len) =>
    change = ta.change(src)
    gain = ta.rma(math.max(change, 0), len)
    loss = ta.rma(-math.min(change, 0), len)
    100 - (100 / (1 + gain / loss))

// --- Begin: main.pine ---
r = __indicators_rsi__customRsi(close, 14)
plot(__utils_math__round(r, 2))
```

---

## MVP Scope (v1)

### In Scope

1. **Core Bundling**
   - Entry point configuration
   - Import resolution from `// @import` directives
   - Dependency graph construction
   - Identifier renaming with file-based prefixes
   - Single file output

2. **Module System**
   - Comment-based `// @import { x } from "./path.pine"` syntax
   - Comment-based `// @export functionName` syntax
   - Named exports only (no default exports in v1)

3. **CLI**
   - `pinebundle build` - compile to output
   - `pinebundle build --watch` - rebuild on file changes
   - Basic config file support (`pine.config.json`)

4. **Validation**
   - Error if exported identifier doesn't exist
   - Error if imported identifier isn't exported
   - Error on circular dependencies (or handle gracefully)
   - Warn on duplicate exports across files

5. **Developer Experience**
   - Errors point to original file and line number
   - `--copy` flag to copy output to clipboard

### Out of Scope for v1

- Tree shaking / dead code elimination
- Minification
- Type checking
- TradingView sync
- VS Code extension
- Multi-output builds
- Source maps
- Native TradingView library imports (leave `import user/lib/1` alone)

---

## Technical Decisions

### Language: Python

**Rationale:**
- pynescript is Python; direct integration via `import pynescript`
- Alternative (JavaScript) would require subprocess calls or porting the parser
- Performance is irrelevant at this scale (bundling 10-50 small files)
- Distribution via pip is adequate; can add PyInstaller later for standalone binary

### Identifier Renaming Strategy

Use file path to generate prefix:
- `src/utils/math.pine` → `__utils_math__`
- `src/indicators/rsi.pine` → `__indicators_rsi__`

What gets renamed:
- Exported function names
- Exported variable names
- References to those functions/variables in importing files

What doesn't get renamed:
- Function parameters
- Local variables inside functions
- Built-in PineScript functions (`ta.rsi`, `math.max`, etc.)
- Variables/functions that aren't exported

### Dependency Resolution

1. Parse entry file
2. Extract `// @import` comments
3. Resolve relative paths to absolute paths
4. Recursively parse imported files
5. Build directed graph of dependencies
6. Topological sort (Kahn's algorithm or DFS)
7. Detect cycles and error

---

## Risk Assessment

### Known Risks

1. **pynescript API gaps**: Haven't used it hands-on. Might not expose enough AST detail for our needs.

2. **Comment preservation**: Need `// @import` directives to survive parsing. pynescript appears to preserve annotations, but need to verify.

3. **PineScript scoping edge cases**: Variables in `if` blocks, `for` loops, `switch` statements. Need to understand what's global vs local.

4. **UDT and method handling**: PineScript v5+ has user-defined types. These need proper namespacing too.

### Mitigation

Spike the riskiest part first before building the full CLI.

---

## The Spike

### Goal

Prove that the core technical approach works before investing in the full implementation.

### What We'll Do

1. Create two minimal `.pine` files that would have naming collisions
2. Parse both with pynescript
3. Walk the ASTs and rename identifiers
4. Merge the ASTs
5. Unparse to a single output
6. Manually verify the output is valid PineScript (paste into TradingView)

### File 1: `helpers.pine`

```pine
//@version=5
// @export calculate

calculate(x) =>
    x * 2

helper = 10
```

### File 2: `main.pine`

```pine
//@version=5
// @import { calculate } from "./helpers.pine"

indicator("Test", overlay=true)

calculate(x) =>  // Local function with same name - should NOT be renamed
    x + 100

myVal = calculate(close)  // Uses local
otherVal = calculate(14)  // Should use imported (renamed) version... 

// Actually, this reveals a design question - see below
```

### Design Question the Spike Will Surface

If `main.pine` has its own `calculate` function AND imports `calculate` from helpers, what happens?

Options:
1. Error: "calculate already defined locally"
2. Imported version gets prefix, local doesn't: use `helpers__calculate()` explicitly
3. Imported version shadows local (probably bad)

This is the kind of thing we need to figure out during the spike.

### Simpler Spike (Start Here)

Actually, let's start simpler to validate the mechanics:

**File 1: `math_utils.pine`**
```pine
//@version=5
// @export double

double(x) =>
    x * 2
```

**File 2: `main.pine`**
```pine
//@version=5
// @import { double } from "./math_utils.pine"

indicator("Test", overlay=true)

result = double(close)
plot(result)
```

**Expected output:**
```pine
//@version=5
indicator("Test", overlay=true)

__math_utils__double(x) =>
    x * 2

result = __math_utils__double(close)
plot(result)
```

### Spike Success Criteria

1. pynescript can parse both files without error
2. We can identify the `double` function definition in the AST
3. We can rename `double` to `__math_utils__double` in the AST
4. We can find references to `double` in main.pine's AST
5. We can update those references to `__math_utils__double`
6. pynescript can unparse the modified/merged AST
7. The output is valid PineScript (TradingView accepts it)

### Spike Implementation Steps

```python
# Step 1: Install pynescript
# pip install pynescript

# Step 2: Parse a file and inspect the AST
from pynescript import parse, unparse, dump

with open("math_utils.pine") as f:
    source = f.read()

ast = parse(source)
print(dump(ast))  # See what we're working with

# Step 3: Figure out how to:
# - Find function definitions (look for FunctionDef or similar nodes)
# - Find identifier references (Name nodes?)
# - Modify node attributes (rename id='double' to id='__math_utils__double')

# Step 4: Unparse and verify
output = unparse(modified_ast)
print(output)
```

---

## Next Steps

1. **Run the spike** - Install pynescript, parse sample files, explore the AST structure
2. **Document findings** - What AST nodes exist? How are functions represented? How are references represented?
3. **Build minimal prototype** - Hard-coded two-file bundle, no CLI, no config
4. **Iterate to MVP** - Add CLI, config file, proper error handling
5. **Release and gather feedback** - See what real users need

---

## Open Questions

1. Should we support wildcard imports? `// @import * from "./utils.pine"`
2. How do we handle PineScript's `var` and `varip` declarations?
3. Should the bundler validate PineScript version consistency across files?
4. What's the right behavior for `input()` calls in non-entry files?
5. Should we preserve or strip `// @export` comments in output?
6. How do we handle type definitions (UDTs) - do they need namespacing?

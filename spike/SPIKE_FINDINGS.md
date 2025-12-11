# Pinecone Spike Findings

## Executive Summary

**The spike is successful.** The core technical approach works:
- pynescript correctly parses PineScript to AST
- We can walk and modify the AST (rename identifiers)
- pynescript correctly unparses modified ASTs back to valid PineScript
- Multi-file bundling with namespacing works

## Key Technical Findings

### 1. pynescript API

The correct import path is `pynescript.ast`, not `pynescript` directly:

```python
from pynescript.ast import parse, unparse, dump, NodeTransformer
```

Key functions:
- `parse(source: str) -> Script` - Parse PineScript source to AST
- `unparse(ast: Script) -> str` - Convert AST back to PineScript source
- `dump(ast) -> str` - Pretty-print AST for debugging
- `NodeTransformer` - Base class for AST transformation (like Python's ast module)

### 2. AST Structure

**Script** (root node):
- `body: list[stmt]` - List of statement nodes
- `annotations: list[str]` - List of annotations like `//@version=5`

**FunctionDef** (function definition):
- `name: str` - Function name (can be modified!)
- `args: list[Param]` - Function parameters
- `body: list[stmt]` - Function body statements
- `export: int` - Export flag (0 or 1)
- `annotations: list[str]` - Function annotations

**Name** (identifier reference):
- `id: str` - Identifier name (can be modified!)
- `ctx: Load | Store` - Context (reading vs writing)

### 3. Comment Handling

**Critical finding:** pynescript strips regular comments during parsing.

- `//@version=5` is preserved as an annotation
- `// @export ...` and `// @import ...` are stripped

**Solution:** Parse directive comments from raw source BEFORE calling pynescript:
```python
def parse_export_directive(source: str) -> ExportDirective:
    match = re.search(r'//\s*@export\s+(.+)$', source, re.MULTILINE)
    ...
```

### 4. NodeTransformer Pattern

Works similarly to Python's `ast.NodeTransformer`:

```python
class IdentifierRenamer(NodeTransformer):
    def __init__(self, renames: dict[str, str]):
        self.renames = renames
        super().__init__()

    def visit_FunctionDef(self, node: FunctionDef):
        if node.name in self.renames:
            node.name = self.renames[node.name]
        self.generic_visit(node)  # Visit children
        return node

    def visit_Name(self, node: Name):
        if node.id in self.renames and isinstance(node.ctx, Load):
            node.id = self.renames[node.id]
        return node
```

### 5. Unparsing Quirks

- `unparse()` expects a `Script` node, not individual statements
- Multi-line function bodies get preserved correctly
- Whitespace/formatting is normalized but valid

## Validated Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| Parse single file | ✅ Works | `parse()` handles PineScript v5 |
| Unparse single file | ✅ Works | Round-trip preserves semantics |
| Parse @export directives | ✅ Works | Regex on raw source |
| Parse @import directives | ✅ Works | Regex on raw source |
| Rename function definitions | ✅ Works | Modify `FunctionDef.name` |
| Rename function references | ✅ Works | Modify `Name.id` with `Load` ctx |
| Multi-file bundling | ✅ Works | Merge AST body lists |
| Nested directories | ✅ Works | `src/utils/format.pine` → `__utils_format__` |

## Design Decisions Confirmed

### Identifier Renaming Strategy

File path to prefix conversion works well:
- `src/math_utils.pine` → `__math_utils__`
- `src/indicators/custom_rsi.pine` → `__indicators_custom_rsi__`

This avoids collisions while keeping names readable in debugging.

### What Gets Renamed

- ✅ Exported function names (FunctionDef.name)
- ✅ References to exported functions (Name.id with Load context)

### What Doesn't Get Renamed

- ✅ Function parameters (stay as-is, scoped to function)
- ✅ Local variables inside functions (scoped)
- ✅ Built-ins like `ta.rsi`, `math.max` (not in rename map)
- ✅ Non-exported functions/variables (not in export directive)

## Open Questions Resolved

### Q: How do we handle local functions with same name as import?

**Answer:** With our approach, imports are always prefixed. If `main.pine` has:
- Local `calculate()` function
- Import `calculate` from helpers

The imported version becomes `__helpers__calculate`, so there's no collision.
User must explicitly use the prefixed name for the import.

**Recommendation:** In v1, require explicit usage. Could add aliasing later:
```pine
// @import { calculate as helperCalc } from "./helpers.pine"
```

## Known Limitations

1. **No variable exports yet** - Only tested function exports. Variable handling (especially `var`/`varip`) needs validation.

2. **No transitive dependencies** - Current spike only handles direct imports. Need to implement recursive resolution.

3. **No circular dependency detection** - Would loop forever currently.

4. **No validation** - Doesn't check if exported identifier actually exists in AST.

5. **No error handling** - File not found, parse errors, etc. not handled gracefully.

## Files Produced

```
spike/
├── src/
│   ├── main.pine                    # Simple test entry
│   ├── main_complex.pine            # Complex test entry
│   ├── math_utils.pine              # Simple module
│   ├── indicators/
│   │   └── custom_rsi.pine          # Nested module
│   └── utils/
│       └── format.pine              # Multiple exports
├── dist/
│   ├── output.pine                  # Simple bundle output
│   └── complex_output.pine          # Complex bundle output
├── spike.py                         # Spike implementation
├── explore_ast.py                   # AST exploration script
└── SPIKE_FINDINGS.md               # This document
```

## Spike Success Criteria Checklist

From the spec:

- [x] pynescript can parse both files without error
- [x] We can identify the `double` function definition in the AST
- [x] We can rename `double` to `__math_utils__double` in the AST
- [x] We can find references to `double` in main.pine's AST
- [x] We can update those references to `__math_utils__double`
- [x] pynescript can unparse the modified/merged AST
- [ ] The output is valid PineScript (TradingView accepts it) - **Manual verification needed**

## Recommendation

**Proceed to MVP implementation.** The spike proves the core approach is sound.

### Priority Order for MVP:

1. **CLI foundation** - Basic `pinebundle build` command
2. **Recursive imports** - Handle transitive dependencies
3. **Validation** - Check exports exist, imports valid
4. **Error handling** - Helpful error messages with line numbers
5. **Cycle detection** - Error on circular dependencies
6. **Config file** - `pine.config.json` support
7. **Watch mode** - Rebuild on changes

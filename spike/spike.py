#!/usr/bin/env python3
"""
Pinecone Spike: Proof of concept for PineScript bundler.

Goals:
1. Parse @export and @import directives from comments (before pynescript strips them)
2. Parse PineScript files to AST
3. Rename exported identifiers with file-based prefixes
4. Update references to renamed identifiers
5. Merge ASTs into single output
6. Unparse to valid PineScript
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from pynescript.ast import parse, unparse, NodeTransformer, Name, FunctionDef, Load


# =============================================================================
# DIRECTIVE PARSING
# =============================================================================

@dataclass
class ExportDirective:
    """Represents a // @export directive."""
    names: list[str]  # exported identifiers


@dataclass
class ImportDirective:
    """Represents a // @import directive."""
    names: list[str]  # imported identifiers
    from_path: str    # relative path to module


def parse_export_directive(source: str) -> Optional[ExportDirective]:
    """Extract @export directive from source."""
    # Match: // @export name1, name2, name3
    match = re.search(r'//\s*@export\s+(.+)$', source, re.MULTILINE)
    if match:
        names_str = match.group(1)
        names = [n.strip() for n in names_str.split(',')]
        return ExportDirective(names=names)
    return None


def parse_import_directives(source: str) -> list[ImportDirective]:
    """Extract all @import directives from source."""
    # Match: // @import { name1, name2 } from "./path.pine"
    pattern = r'//\s*@import\s*\{\s*([^}]+)\s*\}\s*from\s*["\']([^"\']+)["\']'
    imports = []
    for match in re.finditer(pattern, source):
        names_str = match.group(1)
        from_path = match.group(2)
        names = [n.strip() for n in names_str.split(',')]
        imports.append(ImportDirective(names=names, from_path=from_path))
    return imports


# =============================================================================
# IDENTIFIER RENAMING
# =============================================================================

def file_to_prefix(filepath: str) -> str:
    """Convert file path to identifier prefix.

    Examples:
        src/utils/math.pine -> __utils_math__
        src/indicators/rsi.pine -> __indicators_rsi__
    """
    path = Path(filepath)
    # Remove src/ prefix if present, and .pine extension
    parts = list(path.parts)
    if parts and parts[0] == 'src':
        parts = parts[1:]

    # Remove .pine extension from last part
    if parts:
        parts[-1] = parts[-1].replace('.pine', '')

    return '__' + '_'.join(parts) + '__'


class IdentifierRenamer(NodeTransformer):
    """Rename identifiers in AST."""

    def __init__(self, renames: dict[str, str]):
        """
        Args:
            renames: Dict mapping old names to new names
        """
        self.renames = renames
        super().__init__()

    def visit_FunctionDef(self, node: FunctionDef):
        """Rename function definitions."""
        if node.name in self.renames:
            node.name = self.renames[node.name]
        # Continue visiting children
        self.generic_visit(node)
        return node

    def visit_Name(self, node: Name):
        """Rename name references."""
        if node.id in self.renames and isinstance(node.ctx, Load):
            node.id = self.renames[node.id]
        return node


# =============================================================================
# BUNDLING
# =============================================================================

@dataclass
class ParsedModule:
    """A parsed PineScript module."""
    filepath: str
    source: str
    ast: object  # Script AST node
    exports: Optional[ExportDirective]
    imports: list[ImportDirective]


def parse_module(filepath: str) -> ParsedModule:
    """Parse a PineScript file into a module."""
    with open(filepath) as f:
        source = f.read()

    exports = parse_export_directive(source)
    imports = parse_import_directives(source)
    ast = parse(source)

    return ParsedModule(
        filepath=filepath,
        source=source,
        ast=ast,
        exports=exports,
        imports=imports
    )


def bundle(entry_path: str) -> str:
    """Bundle PineScript files starting from entry point.

    Returns bundled PineScript source.
    """
    base_dir = Path(entry_path).parent

    # Step 1: Parse entry file
    print(f"[1] Parsing entry: {entry_path}")
    entry = parse_module(entry_path)

    # Step 2: Parse imported modules
    modules: dict[str, ParsedModule] = {}
    for imp in entry.imports:
        module_path = str(base_dir / imp.from_path)
        print(f"[2] Parsing import: {module_path}")
        modules[module_path] = parse_module(module_path)

    # Step 3: Build rename map for all exports
    renames: dict[str, str] = {}
    for path, module in modules.items():
        if module.exports:
            prefix = file_to_prefix(path)
            for name in module.exports.names:
                new_name = prefix + name
                renames[name] = new_name
                print(f"[3] Rename: {name} -> {new_name}")

    # Step 4: Rename identifiers in imported modules
    for path, module in modules.items():
        if module.exports:
            prefix = file_to_prefix(path)
            # Only rename the exports from this specific module
            module_renames = {
                name: prefix + name
                for name in module.exports.names
            }
            renamer = IdentifierRenamer(module_renames)
            renamer.visit(module.ast)
            print(f"[4] Renamed exports in: {path}")

    # Step 5: Rename references in entry file
    renamer = IdentifierRenamer(renames)
    renamer.visit(entry.ast)
    print(f"[5] Renamed references in entry")

    # Step 6: Merge ASTs
    # Strategy: Collect all body statements, module code first, then entry code
    merged_body = []

    # Add module code (skip version annotations, we'll use entry's)
    for path, module in modules.items():
        merged_body.extend(module.ast.body)

    # Add entry code (skip indicator call, put at top)
    indicator_calls = []
    other_statements = []
    for stmt in entry.ast.body:
        # Check if this is an indicator/strategy call
        if hasattr(stmt, 'value') and hasattr(stmt.value, 'func'):
            func = stmt.value.func
            if hasattr(func, 'id') and func.id in ('indicator', 'strategy', 'library'):
                indicator_calls.append(stmt)
                continue
        other_statements.append(stmt)

    # Step 7: Build output
    # Get version from entry
    version = entry.ast.annotations[0] if entry.ast.annotations else '//@version=5'

    # Build output manually since we need to interleave things
    output_lines = [version]

    # Indicator call should come early
    for stmt in indicator_calls:
        output_lines.append(unparse_single(stmt))

    output_lines.append('')
    output_lines.append('// --- Bundled modules ---')

    # Module code
    for path, module in modules.items():
        output_lines.append(f'// --- From: {Path(path).name} ---')
        for stmt in module.ast.body:
            output_lines.append(unparse_single(stmt))

    output_lines.append('')
    output_lines.append('// --- Main ---')
    for stmt in other_statements:
        output_lines.append(unparse_single(stmt))

    return '\n'.join(output_lines)


def unparse_single(node) -> str:
    """Unparse a single statement node."""
    # Create a minimal Script wrapper to unparse single statements
    # This is a workaround since unparse() expects a Script node
    from pynescript.ast.grammar.asdl.generated.PinescriptASTNode import Script
    wrapper = Script(body=[node], annotations=[])
    result = unparse(wrapper)
    # Remove any version annotations that might sneak in
    lines = [l for l in result.split('\n') if not l.startswith('//@version')]
    return '\n'.join(lines)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("PINECONE SPIKE - PineScript Bundler Proof of Concept")
    print("=" * 60)
    print()

    # Test directive parsing
    print("Testing directive parsing:")
    test_export = "// @export double, triple"
    print(f"  Export: {parse_export_directive(test_export)}")

    test_import = '// @import { foo, bar } from "./utils.pine"'
    print(f"  Import: {parse_import_directives(test_import)}")

    print()
    print("Testing file_to_prefix:")
    print(f"  src/math_utils.pine -> {file_to_prefix('src/math_utils.pine')}")
    print(f"  src/utils/helpers.pine -> {file_to_prefix('src/utils/helpers.pine')}")

    print()
    print("=" * 60)
    print("BUNDLING")
    print("=" * 60)
    print()

    output = bundle('src/main.pine')

    print()
    print("=" * 60)
    print("OUTPUT")
    print("=" * 60)
    print()
    print(output)

    # Write output
    with open('dist/output.pine', 'w') as f:
        f.write(output)
    print()
    print(f"Written to: dist/output.pine")

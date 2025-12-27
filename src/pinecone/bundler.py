"""Main bundler orchestration."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pynescript.ast import unparse
from pynescript.ast.grammar.asdl.generated.PinescriptASTNode import Script
from pynescript.ast.node import Import

from pinecone.config import PineconeConfig
from pinecone.renamer import (
    IdentifierRenamer,
    build_rename_map,
    extract_top_level_identifiers,
)
from pinecone.resolver import DependencyGraph, Module, resolve_dependencies


@dataclass
class BundleResult:
    """Result of bundling operation."""

    output: str
    modules_count: int
    entry_path: Path
    output_path: Path


def unparse_single(node: Any) -> str:
    """Unparse a single AST statement node.

    pynescript's unparse() expects a Script node, so we wrap single statements.

    Args:
        node: An AST statement node.

    Returns:
        PineScript source string.
    """
    wrapper = Script(body=[node], annotations=[])
    result = unparse(wrapper)
    # Remove any version annotations that might appear
    lines = [line for line in result.split("\n") if not line.startswith("//@version")]
    return "\n".join(lines)


def _extract_declaration(entry: Module) -> tuple[Any | None, list[Any]]:
    """Extract indicator/strategy declaration from entry module.

    The indicator() or strategy() call should appear near the top of output.

    Args:
        entry: The entry module.

    Returns:
        Tuple of (declaration_stmt, other_stmts).
    """
    declaration = None
    other = []

    for stmt in entry.ast.body:
        # Check if this is an indicator/strategy/library call
        if hasattr(stmt, "value") and hasattr(stmt.value, "func"):
            func = stmt.value.func
            if hasattr(func, "id") and func.id in ("indicator", "strategy", "library"):
                declaration = stmt
                continue
        other.append(stmt)

    return declaration, other


def _get_version(entry: Module) -> str:
    """Get version annotation from entry module.

    Args:
        entry: The entry module.

    Returns:
        Version string like '//@version=5'.
    """
    if entry.ast.annotations:
        return entry.ast.annotations[0]
    return "//@version=5"


def _extract_external_imports(module: Module) -> list[Import]:
    """Extract external TradingView import statements from a module.

    Args:
        module: The module to extract imports from.

    Returns:
        List of Import AST nodes.
    """
    imports = []
    for stmt in module.ast.body:
        if isinstance(stmt, Import):
            imports.append(stmt)
    return imports


def _deduplicate_imports(all_imports: list[Import]) -> list[Import]:
    """Deduplicate external imports, keeping the first occurrence.

    If the same library is imported with different aliases, keeps the first one.

    Args:
        all_imports: List of all Import nodes from all modules.

    Returns:
        Deduplicated list of Import nodes.
    """
    seen: dict[str, Import] = {}
    for imp in all_imports:
        # Create unique key from namespace/name/version
        key = f"{imp.namespace}/{imp.name}/{imp.version}"
        if key not in seen:
            seen[key] = imp
    return list(seen.values())


def _is_external_import(stmt: Any) -> bool:
    """Check if a statement is an external TradingView import.

    Args:
        stmt: An AST statement node.

    Returns:
        True if this is an external import statement.
    """
    return isinstance(stmt, Import)


def _postprocess_output(output: str) -> str:
    """Apply post-processing fixes to bundled output.

    Fixes known issues with pynescript's unparser:
    - Generic type function calls: `array.new < type > args` -> `array.new<type>(args)`

    Args:
        output: The raw bundled output string.

    Returns:
        Post-processed output with fixes applied.
    """
    # Fix generic type function calls
    # Pattern matches: identifier.new < type > args
    # Where args can be a single number or comma-separated numbers
    # Examples: array.new < line > 500 -> array.new<line>(500)
    #           matrix.new < float > 0, 0 -> matrix.new<float>(0, 0)
    pattern = r"(\w+\.new)\s*<\s*(\w+)\s*>\s*(\d+(?:\s*,\s*\d+)*)"
    replacement = r"\1<\2>(\3)"
    output = re.sub(pattern, replacement, output)

    return output


def bundle(config: PineconeConfig) -> BundleResult:
    """Bundle PineScript files into a single output.

    Pipeline:
    1. Resolve dependencies (build graph, topological sort)
    2. Rename exported identifiers in each module
    3. Rename imported references in each module
    4. Merge ASTs in topological order
    5. Unparse to final output

    Args:
        config: Project configuration.

    Returns:
        BundleResult with output string and metadata.

    Raises:
        ModuleNotFoundError: If an imported module doesn't exist.
        ExportNotFoundError: If an imported name isn't exported.
        CircularDependencyError: If circular imports detected.
        ParseError: If a file fails to parse.
    """
    # Step 1: Resolve all dependencies
    graph = resolve_dependencies(config.entry, config.root_dir)
    entry_path = config.entry.resolve()

    # Step 2: Build rename maps for all dependency modules (not entry)
    # We rename ALL top-level identifiers to avoid collisions when bundled
    all_renames: dict[str, str] = {}
    module_renames: dict[Path, dict[str, str]] = {}

    for module_path in graph.order:
        # Skip the entry module - its identifiers stay as-is
        if module_path == entry_path:
            continue

        module = graph.modules[module_path]
        # Extract ALL top-level identifiers, not just exported ones
        all_identifiers = extract_top_level_identifiers(module.ast)

        if all_identifiers:
            renames = build_rename_map(
                all_identifiers,
                module_path,
                config.root_dir,
            )
            module_renames[module_path] = renames
            all_renames.update(renames)

    # Step 3: Rename all identifiers in each dependency module's AST
    for module_path, renames in module_renames.items():
        module = graph.modules[module_path]
        renamer = IdentifierRenamer(renames)
        renamer.visit(module.ast)

    # Step 4: Rename imported references in all modules (including entry)
    # This updates references to imported names to use their prefixed versions
    for module_path in graph.order:
        module = graph.modules[module_path]
        # Only rename references to imports this module uses
        module_imports = {
            name: path for imp in module.imports for name in imp.names for path in [imp.from_path]
        }
        # Filter all_renames to only include names this module imports
        import_renames = {
            name: all_renames[name] for name in module_imports if name in all_renames
        }
        if import_renames:
            renamer = IdentifierRenamer(import_renames)
            renamer.visit(module.ast)

    # Step 5: Collect and deduplicate external imports from all modules
    all_external_imports: list[Import] = []
    for module_path in graph.order:
        module = graph.modules[module_path]
        all_external_imports.extend(_extract_external_imports(module))

    unique_imports = _deduplicate_imports(all_external_imports)

    # Step 6: Build output
    output_lines = []

    # Version annotation
    version = _get_version(graph.entry)
    output_lines.append(version)

    # Declaration (indicator/strategy) at top
    declaration, entry_other = _extract_declaration(graph.entry)
    if declaration:
        output_lines.append(unparse_single(declaration))

    # External imports (deduplicated) - must come after indicator/strategy declaration
    if unique_imports:
        for imp in unique_imports:
            import_str = f"import {imp.namespace}/{imp.name}/{imp.version}"
            if imp.alias:
                import_str += f" as {imp.alias}"
            output_lines.append(import_str)

    output_lines.append("")

    # Bundled modules (in topological order, excluding entry)
    dependency_modules = [p for p in graph.order if p != entry_path]

    if dependency_modules:
        output_lines.append("// --- Bundled modules ---")

        for module_path in dependency_modules:
            module = graph.modules[module_path]
            output_lines.append(f"// --- From: {module_path.name} ---")

            for stmt in module.ast.body:
                # Skip external import statements (already emitted above)
                if _is_external_import(stmt):
                    continue
                unparsed = unparse_single(stmt)
                if unparsed.strip():  # Skip empty lines
                    output_lines.append(unparsed)

        output_lines.append("")

    # Entry module code (excluding declaration which is already at top)
    output_lines.append("// --- Main ---")
    for stmt in entry_other:
        # Skip external import statements (already emitted above)
        if _is_external_import(stmt):
            continue
        unparsed = unparse_single(stmt)
        if unparsed.strip():
            output_lines.append(unparsed)

    output = "\n".join(output_lines)

    # Step 7: Apply post-processing fixes
    output = _postprocess_output(output)

    return BundleResult(
        output=output,
        modules_count=len(graph.modules),
        entry_path=config.entry,
        output_path=config.output,
    )


def write_bundle(result: BundleResult) -> None:
    """Write bundle result to output file.

    Creates output directory if it doesn't exist.

    Args:
        result: Bundle result to write.
    """
    # Create output directory if needed
    result.output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    result.output_path.write_text(result.output)

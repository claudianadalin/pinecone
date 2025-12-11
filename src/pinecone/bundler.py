"""Main bundler orchestration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pynescript.ast import unparse
from pynescript.ast.grammar.asdl.generated.PinescriptASTNode import Script

from pinecone.config import PineconeConfig
from pinecone.renamer import IdentifierRenamer, build_rename_map
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

    # Step 2: Build complete rename map for all modules
    all_renames: dict[str, str] = {}
    module_renames: dict[Path, dict[str, str]] = {}

    for module_path in graph.order:
        module = graph.modules[module_path]
        if module.exported_names:
            renames = build_rename_map(
                module.exported_names,
                module_path,
                config.root_dir,
            )
            module_renames[module_path] = renames
            all_renames.update(renames)

    # Step 3: Rename identifiers in each module's AST
    for module_path, renames in module_renames.items():
        module = graph.modules[module_path]
        renamer = IdentifierRenamer(renames)
        renamer.visit(module.ast)

    # Step 4: Rename imported references in all modules (including entry)
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

    # Step 5: Build output
    output_lines = []

    # Version annotation
    version = _get_version(graph.entry)
    output_lines.append(version)

    # Declaration (indicator/strategy) at top
    declaration, entry_other = _extract_declaration(graph.entry)
    if declaration:
        output_lines.append(unparse_single(declaration))

    output_lines.append("")

    # Bundled modules (in topological order, excluding entry)
    entry_path = config.entry.resolve()
    dependency_modules = [p for p in graph.order if p != entry_path]

    if dependency_modules:
        output_lines.append("// --- Bundled modules ---")

        for module_path in dependency_modules:
            module = graph.modules[module_path]
            output_lines.append(f"// --- From: {module_path.name} ---")

            for stmt in module.ast.body:
                unparsed = unparse_single(stmt)
                if unparsed.strip():  # Skip empty lines
                    output_lines.append(unparsed)

        output_lines.append("")

    # Entry module code (excluding declaration which is already at top)
    output_lines.append("// --- Main ---")
    for stmt in entry_other:
        unparsed = unparse_single(stmt)
        if unparsed.strip():
            output_lines.append(unparsed)

    output = "\n".join(output_lines)

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

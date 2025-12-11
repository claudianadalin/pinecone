"""Dependency resolution and graph building."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pynescript.ast import parse

from pinecone.directives import (
    ExportDirective,
    ImportDirective,
    parse_exports,
    parse_imports,
)
from pinecone.errors import (
    CircularDependencyError,
    ExportNotFoundError,
    ModuleNotFoundError,
    ParseError,
)


@dataclass
class Module:
    """A parsed PineScript module."""

    path: Path
    source: str
    ast: Any  # pynescript Script node
    exports: list[ExportDirective]
    imports: list[ImportDirective]

    @property
    def exported_names(self) -> list[str]:
        """Get flat list of all exported names."""
        return [name for exp in self.exports for name in exp.names]


@dataclass
class DependencyGraph:
    """Dependency graph for a PineScript project."""

    entry: Module
    modules: dict[Path, Module] = field(default_factory=dict)
    order: list[Path] = field(default_factory=list)


def parse_module(path: Path) -> Module:
    """Parse a PineScript file into a Module.

    Args:
        path: Path to the .pine file.

    Returns:
        Parsed Module object.

    Raises:
        ParseError: If pynescript fails to parse the file.
    """
    source = path.read_text()

    # Parse directives from raw source (before pynescript strips comments)
    exports = parse_exports(source)
    imports = parse_imports(source)

    # Parse AST with pynescript
    try:
        ast = parse(source)
    except Exception as e:
        # Try to extract line number from pynescript error
        raise ParseError(
            message=str(e),
            path=path,
            line=None,
        )

    return Module(
        path=path,
        source=source,
        ast=ast,
        exports=exports,
        imports=imports,
    )


def resolve_dependencies(entry_path: Path, root_dir: Path) -> DependencyGraph:
    """Build complete dependency graph starting from entry point.

    Uses DFS to discover all dependencies, detects cycles, and produces
    a topologically sorted order for bundling.

    Args:
        entry_path: Path to the entry point .pine file.
        root_dir: Project root directory for resolving relative imports.

    Returns:
        DependencyGraph with all modules and their topological order.

    Raises:
        ModuleNotFoundError: If an imported file doesn't exist.
        ExportNotFoundError: If an imported name isn't exported.
        CircularDependencyError: If circular imports are detected.
        ParseError: If a file fails to parse.
    """
    # Track modules we've fully processed
    visited: set[Path] = set()
    # Track modules we're currently visiting (for cycle detection)
    visiting: set[Path] = set()
    # Store parsed modules
    modules: dict[Path, Module] = {}
    # Topological order (dependencies before dependents)
    order: list[Path] = []
    # Track the path for cycle error messages
    path_stack: list[Path] = []

    def visit(module_path: Path, from_file: Path | None = None, from_line: int = 0) -> None:
        """DFS visit a module and its dependencies."""
        # Resolve to absolute path
        module_path = module_path.resolve()

        # Check for cycles
        if module_path in visiting:
            # Find where the cycle starts in the stack
            cycle_start = path_stack.index(module_path)
            cycle = path_stack[cycle_start:] + [module_path]
            raise CircularDependencyError(cycle)

        # Skip if already processed
        if module_path in visited:
            return

        # Check file exists
        if not module_path.exists():
            available = []
            if module_path.parent.exists():
                available = [
                    f.name
                    for f in module_path.parent.iterdir()
                    if f.suffix == ".pine"
                ]
            raise ModuleNotFoundError(
                import_path=str(module_path.relative_to(root_dir)),
                from_file=from_file or module_path,
                from_line=from_line,
                available=available,
            )

        # Mark as visiting
        visiting.add(module_path)
        path_stack.append(module_path)

        # Parse the module
        module = parse_module(module_path)
        modules[module_path] = module

        # Process imports (visit dependencies first)
        for imp in module.imports:
            # Resolve import path relative to current module
            import_path = (module_path.parent / imp.from_path).resolve()

            # Visit the dependency
            visit(import_path, from_file=module_path, from_line=imp.line_number)

            # Validate that imported names are actually exported
            dep_module = modules.get(import_path)
            if dep_module:
                for name in imp.names:
                    if name not in dep_module.exported_names:
                        raise ExportNotFoundError(
                            name=name,
                            module_path=import_path,
                            from_file=module_path,
                            from_line=imp.line_number,
                            available_exports=dep_module.exported_names,
                        )

        # Done visiting this module
        visiting.remove(module_path)
        path_stack.pop()
        visited.add(module_path)

        # Add to order (dependencies come before this module)
        order.append(module_path)

    # Start from entry point
    visit(entry_path)

    # Entry module
    entry_module = modules[entry_path.resolve()]

    return DependencyGraph(
        entry=entry_module,
        modules=modules,
        order=order,
    )

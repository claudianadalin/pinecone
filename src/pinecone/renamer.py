"""AST identifier renaming for namespace isolation."""

from pathlib import Path
from typing import Any

from pynescript.ast import Assign, FunctionDef, Name, NodeTransformer, Tuple


def path_to_prefix(path: Path, root_dir: Path) -> str:
    """Convert file path to namespace prefix.

    Removes root_dir prefix, src/ prefix, and .pine extension.

    Args:
        path: Absolute path to the .pine file.
        root_dir: Project root directory.

    Returns:
        Prefix string like '__utils_math__'.

    Examples:
        >>> path_to_prefix(Path('/project/src/utils/math.pine'), Path('/project'))
        '__utils_math__'
        >>> path_to_prefix(Path('/project/src/main.pine'), Path('/project'))
        '__main__'
    """
    # Get path relative to root
    try:
        rel_path = path.relative_to(root_dir)
    except ValueError:
        # If path is not relative to root, use just the filename
        rel_path = Path(path.name)

    # Convert to parts and filter
    parts = list(rel_path.parts)

    # Remove 'src' prefix if present
    if parts and parts[0] == "src":
        parts = parts[1:]

    # Remove .pine extension from last part
    if parts:
        parts[-1] = parts[-1].replace(".pine", "")

    # Join with underscores
    return "__" + "_".join(parts) + "__"


class IdentifierRenamer(NodeTransformer):
    """Rename identifiers in AST.

    Renames function definitions, variable declarations, and their references
    based on a rename map.
    """

    def __init__(self, renames: dict[str, str]) -> None:
        """Initialize renamer.

        Args:
            renames: Mapping from old names to new names.
        """
        self.renames = renames
        super().__init__()

    def visit_FunctionDef(self, node: FunctionDef) -> FunctionDef:
        """Rename function definitions.

        Skips method definitions (node.method is truthy) since methods are
        called via dot notation and don't collide in the global namespace.
        """
        # Skip methods - they're called via dot notation (obj.method())
        # and don't need renaming to avoid collisions
        if node.method:
            self.generic_visit(node)
            return node

        if node.name in self.renames:
            node.name = self.renames[node.name]
        # Continue visiting children (for nested functions, etc.)
        self.generic_visit(node)
        return node

    def visit_Assign(self, node: Assign) -> Assign:
        """Rename variable declarations in assignment statements."""
        self._rename_target(node.target)
        # Continue visiting children (the value expression)
        self.generic_visit(node)
        return node

    def _rename_target(self, target: Any) -> None:
        """Rename an assignment target (handles both single names and tuples)."""
        if isinstance(target, Name) and target.id in self.renames:
            target.id = self.renames[target.id]
        elif isinstance(target, Tuple):
            # Handle tuple unpacking: [a, b] = ...
            for elt in target.elts:
                self._rename_target(elt)

    def visit_Name(self, node: Name) -> Name:
        """Rename name references and declarations."""
        if node.id in self.renames:
            node.id = self.renames[node.id]
        return node


def extract_top_level_identifiers(ast: Any) -> list[str]:
    """Extract all top-level identifier names from a module AST.

    This includes:
    - Variable declarations (Assign)
    - Function definitions (FunctionDef) - but NOT methods
    - Tuple unpacking targets

    Methods are excluded because they're called via dot notation and
    don't collide in the global namespace.

    Args:
        ast: The parsed module AST (Script node).

    Returns:
        List of identifier names defined at the top level.
    """
    identifiers = []

    def extract_from_target(target: Any) -> None:
        """Extract names from an assignment target."""
        if isinstance(target, Name):
            identifiers.append(target.id)
        elif isinstance(target, Tuple):
            for elt in target.elts:
                extract_from_target(elt)

    for stmt in ast.body:
        if isinstance(stmt, Assign):
            extract_from_target(stmt.target)
        elif isinstance(stmt, FunctionDef):
            # Skip methods - they're called via dot notation (obj.method())
            if not stmt.method:
                identifiers.append(stmt.name)

    return identifiers


def build_rename_map(
    names: list[str],
    module_path: Path,
    root_dir: Path,
) -> dict[str, str]:
    """Build rename map for a module's identifiers.

    Args:
        names: List of identifiers to rename.
        module_path: Path to the module file.
        root_dir: Project root directory.

    Returns:
        Dict mapping original names to prefixed names.

    Example:
        >>> build_rename_map(['foo', 'bar'], Path('/project/src/utils.pine'), Path('/project'))
        {'foo': '__utils__foo', 'bar': '__utils__bar'}
    """
    prefix = path_to_prefix(module_path, root_dir)
    return {name: prefix + name for name in names}

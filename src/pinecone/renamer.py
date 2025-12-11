"""AST identifier renaming for namespace isolation."""

from pathlib import Path

from pynescript.ast import FunctionDef, Load, Name, NodeTransformer


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

    Renames function definitions and their references based on a rename map.
    Only renames Name nodes with Load context (references), not Store (assignments).
    """

    def __init__(self, renames: dict[str, str]) -> None:
        """Initialize renamer.

        Args:
            renames: Mapping from old names to new names.
        """
        self.renames = renames
        super().__init__()

    def visit_FunctionDef(self, node: FunctionDef) -> FunctionDef:
        """Rename function definitions."""
        if node.name in self.renames:
            node.name = self.renames[node.name]
        # Continue visiting children (for nested functions, etc.)
        self.generic_visit(node)
        return node

    def visit_Name(self, node: Name) -> Name:
        """Rename name references.

        Only renames references (Load context), not assignments (Store context).
        """
        if node.id in self.renames and isinstance(node.ctx, Load):
            node.id = self.renames[node.id]
        return node


def build_rename_map(
    exported_names: list[str],
    module_path: Path,
    root_dir: Path,
) -> dict[str, str]:
    """Build rename map for a module's exports.

    Args:
        exported_names: List of exported identifiers.
        module_path: Path to the module file.
        root_dir: Project root directory.

    Returns:
        Dict mapping original names to prefixed names.

    Example:
        >>> build_rename_map(['foo', 'bar'], Path('/project/src/utils.pine'), Path('/project'))
        {'foo': '__utils__foo', 'bar': '__utils__bar'}
    """
    prefix = path_to_prefix(module_path, root_dir)
    return {name: prefix + name for name in exported_names}

"""Parse @import and @export directives from PineScript source."""

import re
from dataclasses import dataclass


@dataclass
class ExportDirective:
    """Represents a // @export directive."""

    names: list[str]
    line_number: int


@dataclass
class ImportDirective:
    """Represents a // @import directive."""

    names: list[str]
    from_path: str
    line_number: int


# Regex patterns for directives
EXPORT_PATTERN = re.compile(r"//\s*@export\s+(.+)$", re.MULTILINE)
IMPORT_PATTERN = re.compile(
    r'//\s*@import\s*\{\s*([^}]+)\s*\}\s*from\s*["\']([^"\']+)["\']'
)


def parse_exports(source: str) -> list[ExportDirective]:
    """Extract all @export directives from source with line numbers.

    Args:
        source: PineScript source code.

    Returns:
        List of ExportDirective objects.

    Example:
        >>> source = '''
        ... //@version=5
        ... // @export foo, bar
        ... '''
        >>> exports = parse_exports(source)
        >>> exports[0].names
        ['foo', 'bar']
    """
    exports = []

    for match in EXPORT_PATTERN.finditer(source):
        # Calculate line number (1-indexed)
        line_number = source[: match.start()].count("\n") + 1

        # Parse comma-separated names
        names_str = match.group(1)
        names = [name.strip() for name in names_str.split(",") if name.strip()]

        if names:
            exports.append(ExportDirective(names=names, line_number=line_number))

    return exports


def parse_imports(source: str) -> list[ImportDirective]:
    """Extract all @import directives from source with line numbers.

    Args:
        source: PineScript source code.

    Returns:
        List of ImportDirective objects.

    Example:
        >>> source = '''
        ... //@version=5
        ... // @import { foo, bar } from "./utils.pine"
        ... '''
        >>> imports = parse_imports(source)
        >>> imports[0].names
        ['foo', 'bar']
        >>> imports[0].from_path
        './utils.pine'
    """
    imports = []

    for match in IMPORT_PATTERN.finditer(source):
        # Calculate line number (1-indexed)
        line_number = source[: match.start()].count("\n") + 1

        # Parse comma-separated names
        names_str = match.group(1)
        names = [name.strip() for name in names_str.split(",") if name.strip()]

        # Get the import path
        from_path = match.group(2)

        if names and from_path:
            imports.append(
                ImportDirective(
                    names=names,
                    from_path=from_path,
                    line_number=line_number,
                )
            )

    return imports


def get_all_exported_names(source: str) -> list[str]:
    """Get a flat list of all exported names from source.

    Args:
        source: PineScript source code.

    Returns:
        List of exported identifier names.
    """
    exports = parse_exports(source)
    return [name for directive in exports for name in directive.names]


def get_all_imported_names(source: str) -> dict[str, str]:
    """Get a mapping of imported names to their source modules.

    Args:
        source: PineScript source code.

    Returns:
        Dict mapping imported name to module path.
    """
    imports = parse_imports(source)
    result = {}
    for directive in imports:
        for name in directive.names:
            result[name] = directive.from_path
    return result

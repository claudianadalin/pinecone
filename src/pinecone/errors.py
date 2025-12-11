"""Custom exceptions for Pinecone bundler."""

from pathlib import Path


class PineconeError(Exception):
    """Base exception for all Pinecone errors."""

    pass


class ConfigError(PineconeError):
    """Raised when there's an issue with the configuration file."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.message = message
        self.path = path
        super().__init__(message)

    def __str__(self) -> str:
        if self.path:
            return f"Config error in {self.path}: {self.message}"
        return f"Config error: {self.message}"


class ParseError(PineconeError):
    """Raised when PineScript parsing fails."""

    def __init__(
        self,
        message: str,
        path: Path,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.message = message
        self.path = path
        self.line = line
        self.column = column
        super().__init__(message)

    def __str__(self) -> str:
        location = str(self.path)
        if self.line is not None:
            location += f":{self.line}"
            if self.column is not None:
                location += f":{self.column}"
        return f"Parse error in {location}: {self.message}"


class ModuleNotFoundError(PineconeError):
    """Raised when an imported module cannot be found."""

    def __init__(
        self,
        import_path: str,
        from_file: Path,
        from_line: int,
        available: list[str] | None = None,
    ) -> None:
        self.import_path = import_path
        self.from_file = from_file
        self.from_line = from_line
        self.available = available or []
        super().__init__(f"Cannot find module '{import_path}'")

    def __str__(self) -> str:
        lines = [
            f"Cannot find module \"{self.import_path}\"",
            f"",
            f"  → Imported from: {self.from_file}:{self.from_line}",
        ]
        if self.available:
            lines.append("")
            lines.append("Available files in directory:")
            for f in self.available[:5]:  # Show max 5 suggestions
                lines.append(f"  • {f}")
        return "\n".join(lines)


class ExportNotFoundError(PineconeError):
    """Raised when an imported name isn't exported by the module."""

    def __init__(
        self,
        name: str,
        module_path: Path,
        from_file: Path,
        from_line: int,
        available_exports: list[str] | None = None,
    ) -> None:
        self.name = name
        self.module_path = module_path
        self.from_file = from_file
        self.from_line = from_line
        self.available_exports = available_exports or []
        super().__init__(f"'{name}' is not exported from '{module_path}'")

    def __str__(self) -> str:
        lines = [
            f"\"{self.name}\" is not exported from \"{self.module_path.name}\"",
            f"",
            f"  → Imported from: {self.from_file}:{self.from_line}",
        ]
        if self.available_exports:
            lines.append("")
            lines.append("Available exports:")
            for exp in self.available_exports:
                lines.append(f"  • {exp}")
        else:
            lines.append("")
            lines.append("This module has no exports. Add // @export to export functions.")
        return "\n".join(lines)


class CircularDependencyError(PineconeError):
    """Raised when a circular import is detected."""

    def __init__(self, cycle: list[Path]) -> None:
        self.cycle = cycle
        super().__init__("Circular dependency detected")

    def __str__(self) -> str:
        cycle_str = " → ".join(str(p.name) for p in self.cycle)
        return f"Circular dependency detected:\n\n  {cycle_str}"


class IdentifierNotFoundError(PineconeError):
    """Raised when an exported identifier doesn't exist in the module's AST."""

    def __init__(
        self,
        name: str,
        module_path: Path,
        export_line: int,
        available_identifiers: list[str] | None = None,
    ) -> None:
        self.name = name
        self.module_path = module_path
        self.export_line = export_line
        self.available_identifiers = available_identifiers or []
        super().__init__(f"Exported identifier '{name}' not found in module")

    def __str__(self) -> str:
        lines = [
            f"Exported identifier \"{self.name}\" not found in module",
            f"",
            f"  → Export directive at: {self.module_path}:{self.export_line}",
        ]
        if self.available_identifiers:
            lines.append("")
            lines.append("Available identifiers in this file:")
            for ident in self.available_identifiers[:5]:
                lines.append(f"  • {ident}")
        return "\n".join(lines)

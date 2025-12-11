"""Configuration file loading and validation."""

import json
from dataclasses import dataclass
from pathlib import Path

from pinecone.errors import ConfigError

CONFIG_FILENAME = "pine.config.json"


@dataclass
class PineconeConfig:
    """Configuration for a Pinecone project."""

    entry: Path
    output: Path
    root_dir: Path

    @property
    def src_dir(self) -> Path:
        """Get the source directory (parent of entry file)."""
        return self.entry.parent


def load_config(config_path: Path | None = None) -> PineconeConfig:
    """Load and validate pine.config.json.

    Args:
        config_path: Optional path to config file. If None, searches current directory.

    Returns:
        PineconeConfig with validated and resolved paths.

    Raises:
        ConfigError: If config file not found, invalid JSON, or missing required fields.
    """
    # Find config file
    if config_path is None:
        config_path = Path.cwd() / CONFIG_FILENAME

    if not config_path.exists():
        raise ConfigError(
            f"Config file not found. Create a {CONFIG_FILENAME} file with 'entry' and 'output' fields.",
            path=config_path,
        )

    # Parse JSON
    try:
        with open(config_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON: {e.msg} at line {e.lineno}",
            path=config_path,
        )

    # Validate required fields
    if not isinstance(data, dict):
        raise ConfigError("Config must be a JSON object", path=config_path)

    missing = []
    if "entry" not in data:
        missing.append("entry")
    if "output" not in data:
        missing.append("output")

    if missing:
        raise ConfigError(
            f"Missing required fields: {', '.join(missing)}",
            path=config_path,
        )

    # Resolve paths relative to config file location
    root_dir = config_path.parent.resolve()
    entry = (root_dir / data["entry"]).resolve()
    output = (root_dir / data["output"]).resolve()

    # Validate entry exists
    if not entry.exists():
        raise ConfigError(
            f"Entry file not found: {data['entry']}",
            path=config_path,
        )

    if not entry.suffix == ".pine":
        raise ConfigError(
            f"Entry file must be a .pine file: {data['entry']}",
            path=config_path,
        )

    return PineconeConfig(
        entry=entry,
        output=output,
        root_dir=root_dir,
    )

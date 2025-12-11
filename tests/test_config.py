"""Tests for configuration loading."""

import json
import pytest
from pathlib import Path

from pinecone.config import load_config, PineconeConfig
from pinecone.errors import ConfigError


class TestLoadConfig:
    """Tests for load_config function."""

    def test_valid_config(self, tmp_path: Path) -> None:
        # Create config file
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({
            "entry": "src/main.pine",
            "output": "dist/bundle.pine"
        }))

        # Create entry file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.pine").write_text("//@version=5")

        config = load_config(config_file)
        assert config.entry == tmp_path / "src" / "main.pine"
        assert config.output == tmp_path / "dist" / "bundle.pine"
        assert config.root_dir == tmp_path

    def test_missing_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "Config file not found" in str(exc_info.value)

    def test_invalid_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text("{ invalid json }")
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "Invalid JSON" in str(exc_info.value)

    def test_missing_entry_field(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({
            "output": "dist/bundle.pine"
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "Missing required fields: entry" in str(exc_info.value)

    def test_missing_output_field(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({
            "entry": "src/main.pine"
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "Missing required fields: output" in str(exc_info.value)

    def test_missing_both_fields(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({}))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "entry" in str(exc_info.value)
        assert "output" in str(exc_info.value)

    def test_entry_file_not_found(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({
            "entry": "src/main.pine",
            "output": "dist/bundle.pine"
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "Entry file not found" in str(exc_info.value)

    def test_entry_file_not_pine(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text(json.dumps({
            "entry": "src/main.txt",
            "output": "dist/bundle.pine"
        }))

        # Create entry file with wrong extension
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.txt").write_text("content")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "must be a .pine file" in str(exc_info.value)

    def test_config_not_object(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pine.config.json"
        config_file.write_text('"just a string"')
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "must be a JSON object" in str(exc_info.value)

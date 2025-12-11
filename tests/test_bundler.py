"""Integration tests for the bundler."""

import pytest
from pathlib import Path

from pinecone.bundler import bundle
from pinecone.config import load_config
from pinecone.errors import CircularDependencyError


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestBundlerIntegration:
    """Integration tests for end-to-end bundling."""

    def test_simple_bundle(self) -> None:
        """Test simple one-import bundle."""
        config = load_config(FIXTURES_DIR / "simple" / "pine.config.json")
        result = bundle(config)

        # Check we got output
        assert result.output is not None
        assert result.modules_count == 2

        # Check output contains renamed function
        assert "__utils__double" in result.output

        # Check output contains version and indicator
        assert "//@version=5" in result.output
        assert 'indicator("Simple Test"' in result.output

        # Check reference was updated
        assert "__utils__double(close)" in result.output

    def test_nested_bundle(self) -> None:
        """Test nested imports (A -> B -> C)."""
        config = load_config(FIXTURES_DIR / "nested" / "pine.config.json")
        result = bundle(config)

        assert result.modules_count == 3

        # Check both modules are included with correct prefixes
        assert "__utils_math__double" in result.output
        assert "__utils_format__formatResult" in result.output

        # Check nested reference is updated (format uses math's double)
        assert "__utils_math__double(x)" in result.output

    def test_circular_dependency_error(self) -> None:
        """Test that circular dependencies raise error."""
        config = load_config(FIXTURES_DIR / "circular" / "pine.config.json")

        with pytest.raises(CircularDependencyError) as exc_info:
            bundle(config)

        # Check error message contains cycle info
        assert "a.pine" in str(exc_info.value)
        assert "b.pine" in str(exc_info.value)

    def test_bundle_preserves_version(self) -> None:
        """Test that version annotation is preserved from entry."""
        config = load_config(FIXTURES_DIR / "simple" / "pine.config.json")
        result = bundle(config)

        assert result.output.startswith("//@version=5")

    def test_bundle_indicator_at_top(self) -> None:
        """Test that indicator() call is near the top."""
        config = load_config(FIXTURES_DIR / "simple" / "pine.config.json")
        result = bundle(config)

        lines = result.output.split("\n")
        # Indicator should be in first few lines
        indicator_line = next(
            i for i, line in enumerate(lines)
            if "indicator(" in line
        )
        assert indicator_line < 5

    def test_bundle_sections_present(self) -> None:
        """Test that section comments are present."""
        config = load_config(FIXTURES_DIR / "simple" / "pine.config.json")
        result = bundle(config)

        assert "// --- Bundled modules ---" in result.output
        assert "// --- From:" in result.output
        assert "// --- Main ---" in result.output

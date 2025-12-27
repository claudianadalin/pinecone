"""Integration tests for the bundler."""

import pytest
from pathlib import Path

from pinecone.bundler import (
    bundle,
    _postprocess_output,
    _deduplicate_imports,
    _extract_external_imports,
)
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


class TestPostprocessOutput:
    """Tests for the _postprocess_output function."""

    def test_fixes_array_new_generic_syntax(self) -> None:
        """Test that array.new<type>(args) syntax is fixed."""
        input_text = "var array<line> lines = array.new < line > 500"
        result = _postprocess_output(input_text)
        assert result == "var array<line> lines = array.new<line>(500)"

    def test_fixes_array_new_with_two_args(self) -> None:
        """Test that array.new<type>(arg1, arg2) syntax is fixed."""
        input_text = "var array<float> arr = array.new < float > 10, 0"
        result = _postprocess_output(input_text)
        assert result == "var array<float> arr = array.new<float>(10, 0)"

    def test_fixes_matrix_new_generic_syntax(self) -> None:
        """Test that matrix.new<type>(args) syntax is fixed."""
        input_text = "var matrix<float> m = matrix.new < float > 3, 3"
        result = _postprocess_output(input_text)
        assert result == "var matrix<float> m = matrix.new<float>(3, 3)"

    def test_preserves_correct_syntax(self) -> None:
        """Test that already correct syntax is preserved."""
        input_text = "var array<line> lines = array.new<line>(500)"
        result = _postprocess_output(input_text)
        assert result == input_text

    def test_fixes_multiple_occurrences(self) -> None:
        """Test that multiple occurrences are all fixed."""
        input_text = """var array<line> a = array.new < line > 100
var array<float> b = array.new < float > 200"""
        result = _postprocess_output(input_text)
        assert "array.new<line>(100)" in result
        assert "array.new<float>(200)" in result

    def test_preserves_other_content(self) -> None:
        """Test that non-generic content is preserved."""
        input_text = """indicator("Test")
x = 1 < 2
y = 3 > 1
var array<line> lines = array.new < line > 500
plot(x)"""
        result = _postprocess_output(input_text)
        assert 'indicator("Test")' in result
        assert "x = 1 < 2" in result
        assert "y = 3 > 1" in result
        assert "array.new<line>(500)" in result
        assert "plot(x)" in result


class TestImportDeduplication:
    """Tests for import deduplication functionality."""

    def test_deduplicate_same_import(self) -> None:
        """Test that duplicate imports are deduplicated."""
        from pynescript.ast.node import Import

        imports = [
            Import(namespace="TradingView", name="ta", version=9, alias="ta"),
            Import(namespace="TradingView", name="ta", version=9, alias=None),
        ]
        result = _deduplicate_imports(imports)
        assert len(result) == 1
        assert result[0].alias == "ta"  # First one is kept

    def test_different_imports_preserved(self) -> None:
        """Test that different imports are all preserved."""
        from pynescript.ast.node import Import

        imports = [
            Import(namespace="TradingView", name="ta", version=9, alias="ta"),
            Import(namespace="TradingView", name="math", version=1, alias=None),
        ]
        result = _deduplicate_imports(imports)
        assert len(result) == 2

    def test_empty_imports(self) -> None:
        """Test that empty import list returns empty."""
        result = _deduplicate_imports([])
        assert result == []

    def test_different_versions_not_deduplicated(self) -> None:
        """Test that same library with different versions are kept separate."""
        from pynescript.ast.node import Import

        imports = [
            Import(namespace="TradingView", name="ta", version=8, alias=None),
            Import(namespace="TradingView", name="ta", version=9, alias=None),
        ]
        result = _deduplicate_imports(imports)
        assert len(result) == 2

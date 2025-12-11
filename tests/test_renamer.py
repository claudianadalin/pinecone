"""Tests for identifier renaming."""

from pathlib import Path

import pytest

from pinecone.renamer import build_rename_map, path_to_prefix


class TestPathToPrefix:
    """Tests for path_to_prefix function."""

    def test_simple_file(self) -> None:
        path = Path("/project/src/utils.pine")
        root = Path("/project")
        # src/ is stripped from prefix for cleaner names
        assert path_to_prefix(path, root) == "__utils__"

    def test_nested_file(self) -> None:
        path = Path("/project/src/utils/math.pine")
        root = Path("/project")
        assert path_to_prefix(path, root) == "__utils_math__"

    def test_strips_src_prefix(self) -> None:
        # src/ should be stripped from the prefix
        path = Path("/project/src/helpers.pine")
        root = Path("/project")
        prefix = path_to_prefix(path, root)
        assert prefix == "__helpers__"

    def test_deep_nesting(self) -> None:
        path = Path("/project/src/indicators/momentum/rsi.pine")
        root = Path("/project")
        assert path_to_prefix(path, root) == "__indicators_momentum_rsi__"


class TestBuildRenameMap:
    """Tests for build_rename_map function."""

    def test_single_export(self) -> None:
        exports = ["myFunc"]
        path = Path("/project/src/utils.pine")
        root = Path("/project")
        renames = build_rename_map(exports, path, root)
        assert renames == {"myFunc": "__utils__myFunc"}

    def test_multiple_exports(self) -> None:
        exports = ["foo", "bar", "baz"]
        path = Path("/project/src/utils.pine")
        root = Path("/project")
        renames = build_rename_map(exports, path, root)
        assert renames == {
            "foo": "__utils__foo",
            "bar": "__utils__bar",
            "baz": "__utils__baz",
        }

    def test_empty_exports(self) -> None:
        renames = build_rename_map([], Path("/project/utils.pine"), Path("/project"))
        assert renames == {}

"""Tests for identifier renaming."""

from pathlib import Path

import pytest
from pynescript.ast import parse

from pinecone.renamer import (
    build_rename_map,
    path_to_prefix,
    extract_top_level_identifiers,
    IdentifierRenamer,
)


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


class TestExtractTopLevelIdentifiers:
    """Tests for extract_top_level_identifiers function."""

    def test_extracts_variable_declarations(self) -> None:
        """Test that variable declarations are extracted."""
        source = """//@version=6
indicator("test")
x = 1
y = 2
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        assert "x" in identifiers
        assert "y" in identifiers

    def test_extracts_function_definitions(self) -> None:
        """Test that function definitions are extracted."""
        source = """//@version=6
indicator("test")
myFunc() => 1
anotherFunc(x) => x * 2
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        assert "myFunc" in identifiers
        assert "anotherFunc" in identifiers

    def test_excludes_method_definitions(self) -> None:
        """Test that method definitions are NOT extracted."""
        source = """//@version=6
indicator("test")
method myMethod(array<int> arr, int x) => arr.push(x)
regularFunc() => 1
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        assert "myMethod" not in identifiers
        assert "regularFunc" in identifiers

    def test_extracts_tuple_unpacking(self) -> None:
        """Test that tuple unpacking variables are extracted."""
        source = """//@version=6
indicator("test")
[a, b] = [1, 2]
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        assert "a" in identifiers
        assert "b" in identifiers

    def test_extracts_var_declarations(self) -> None:
        """Test that var declarations are extracted."""
        source = """//@version=6
indicator("test")
var x = 1
var float y = na
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        assert "x" in identifiers
        assert "y" in identifiers

    def test_empty_module(self) -> None:
        """Test that empty module returns empty list."""
        source = """//@version=6
indicator("test")
"""
        ast = parse(source)
        identifiers = extract_top_level_identifiers(ast)
        # Should only have no variable/function identifiers
        # (indicator is a call, not a definition)
        assert len(identifiers) == 0


class TestIdentifierRenamer:
    """Tests for IdentifierRenamer class."""

    def test_renames_function_definitions(self) -> None:
        """Test that function definitions are renamed."""
        source = """//@version=6
indicator("test")
myFunc() => 1
"""
        ast = parse(source)
        renames = {"myFunc": "__prefix__myFunc"}
        renamer = IdentifierRenamer(renames)
        renamer.visit(ast)

        # Find the function def and check its name
        from pynescript.ast import FunctionDef
        for stmt in ast.body:
            if isinstance(stmt, FunctionDef):
                assert stmt.name == "__prefix__myFunc"

    def test_skips_method_definitions(self) -> None:
        """Test that method definitions are NOT renamed."""
        source = """//@version=6
indicator("test")
method myMethod(array<int> arr) => arr.size()
"""
        ast = parse(source)
        renames = {"myMethod": "__prefix__myMethod"}
        renamer = IdentifierRenamer(renames)
        renamer.visit(ast)

        # Find the method def and check its name is unchanged
        for stmt in ast.body:
            if hasattr(stmt, "name") and hasattr(stmt, "method"):
                if stmt.method:
                    assert stmt.name == "myMethod"  # Should NOT be renamed

    def test_renames_variable_declarations(self) -> None:
        """Test that variable declarations are renamed."""
        source = """//@version=6
indicator("test")
myVar = 1
"""
        ast = parse(source)
        renames = {"myVar": "__prefix__myVar"}
        renamer = IdentifierRenamer(renames)
        renamer.visit(ast)

        # Find the assignment and check target is renamed
        from pynescript.ast import Assign
        for stmt in ast.body:
            if isinstance(stmt, Assign):
                assert stmt.target.id == "__prefix__myVar"

    def test_renames_variable_references(self) -> None:
        """Test that variable references are renamed."""
        source = """//@version=6
indicator("test")
x = 1
y = x + 1
"""
        ast = parse(source)
        renames = {"x": "__prefix__x"}
        renamer = IdentifierRenamer(renames)
        renamer.visit(ast)

        # The reference to x in `y = x + 1` should be renamed
        from pynescript.ast import Assign, BinOp
        for stmt in ast.body:
            if isinstance(stmt, Assign) and hasattr(stmt.target, "id"):
                if stmt.target.id == "y":
                    # Check the left side of the BinOp
                    assert stmt.value.left.id == "__prefix__x"

    def test_renames_tuple_unpacking(self) -> None:
        """Test that tuple unpacking targets are renamed."""
        source = """//@version=6
indicator("test")
[a, b] = [1, 2]
"""
        ast = parse(source)
        renames = {"a": "__prefix__a", "b": "__prefix__b"}
        renamer = IdentifierRenamer(renames)
        renamer.visit(ast)

        # Find the tuple assignment and check targets
        from pynescript.ast import Assign, Tuple
        for stmt in ast.body:
            if isinstance(stmt, Assign) and isinstance(stmt.target, Tuple):
                names = [elt.id for elt in stmt.target.elts]
                assert "__prefix__a" in names
                assert "__prefix__b" in names

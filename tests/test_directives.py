"""Tests for directive parsing."""

import pytest

from pinecone.directives import (
    ExportDirective,
    ImportDirective,
    get_all_exported_names,
    get_all_imported_names,
    parse_exports,
    parse_imports,
)


class TestParseExports:
    """Tests for parse_exports function."""

    def test_single_export(self) -> None:
        source = "// @export myFunc"
        exports = parse_exports(source)
        assert len(exports) == 1
        assert exports[0].names == ["myFunc"]
        assert exports[0].line_number == 1

    def test_multiple_names(self) -> None:
        source = "// @export foo, bar, baz"
        exports = parse_exports(source)
        assert len(exports) == 1
        assert exports[0].names == ["foo", "bar", "baz"]

    def test_export_with_extra_spaces(self) -> None:
        source = "//   @export   foo  ,  bar  "
        exports = parse_exports(source)
        assert len(exports) == 1
        assert exports[0].names == ["foo", "bar"]

    def test_multiple_export_directives(self) -> None:
        source = """
// @export foo
// some comment
// @export bar
"""
        exports = parse_exports(source)
        assert len(exports) == 2
        assert exports[0].names == ["foo"]
        assert exports[1].names == ["bar"]

    def test_line_number_tracking(self) -> None:
        source = """line 1
line 2
// @export myFunc
line 4"""
        exports = parse_exports(source)
        assert exports[0].line_number == 3

    def test_no_exports(self) -> None:
        source = "// just a comment\nsome code"
        exports = parse_exports(source)
        assert len(exports) == 0

    def test_export_in_pinescript_context(self) -> None:
        source = """//@version=5
// @export calculate

calculate(x) =>
    x * 2
"""
        exports = parse_exports(source)
        assert len(exports) == 1
        assert exports[0].names == ["calculate"]


class TestParseImports:
    """Tests for parse_imports function."""

    def test_single_import(self) -> None:
        source = '// @import { foo } from "./utils.pine"'
        imports = parse_imports(source)
        assert len(imports) == 1
        assert imports[0].names == ["foo"]
        assert imports[0].from_path == "./utils.pine"
        assert imports[0].line_number == 1

    def test_multiple_names(self) -> None:
        source = '// @import { foo, bar, baz } from "./utils.pine"'
        imports = parse_imports(source)
        assert len(imports) == 1
        assert imports[0].names == ["foo", "bar", "baz"]

    def test_single_quotes(self) -> None:
        source = "// @import { foo } from './utils.pine'"
        imports = parse_imports(source)
        assert len(imports) == 1
        assert imports[0].from_path == "./utils.pine"

    def test_nested_path(self) -> None:
        source = '// @import { foo } from "./utils/math/helpers.pine"'
        imports = parse_imports(source)
        assert imports[0].from_path == "./utils/math/helpers.pine"

    def test_multiple_imports(self) -> None:
        source = """
// @import { foo } from "./a.pine"
// @import { bar } from "./b.pine"
"""
        imports = parse_imports(source)
        assert len(imports) == 2
        assert imports[0].from_path == "./a.pine"
        assert imports[1].from_path == "./b.pine"

    def test_line_number_tracking(self) -> None:
        source = """line 1
// @import { foo } from "./utils.pine"
line 3"""
        imports = parse_imports(source)
        assert imports[0].line_number == 2

    def test_no_imports(self) -> None:
        source = "// just a comment\nsome code"
        imports = parse_imports(source)
        assert len(imports) == 0

    def test_import_in_pinescript_context(self) -> None:
        source = """//@version=5
// @import { double } from "./math_utils.pine"

indicator("Test", overlay=true)
result = double(close)
"""
        imports = parse_imports(source)
        assert len(imports) == 1
        assert imports[0].names == ["double"]
        assert imports[0].from_path == "./math_utils.pine"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_all_exported_names(self) -> None:
        source = """
// @export foo, bar
// @export baz
"""
        names = get_all_exported_names(source)
        assert set(names) == {"foo", "bar", "baz"}

    def test_get_all_imported_names(self) -> None:
        source = """
// @import { foo } from "./a.pine"
// @import { bar, baz } from "./b.pine"
"""
        mapping = get_all_imported_names(source)
        assert mapping == {
            "foo": "./a.pine",
            "bar": "./b.pine",
            "baz": "./b.pine",
        }

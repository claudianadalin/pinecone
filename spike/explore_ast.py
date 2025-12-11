#!/usr/bin/env python3
"""Explore pynescript AST structure for the spike."""

from pynescript.ast import parse, unparse, dump

# First, let's parse math_utils.pine and see the AST
print("=" * 60)
print("PARSING math_utils.pine")
print("=" * 60)

with open("src/math_utils.pine") as f:
    math_source = f.read()

print("\nSource:")
print(math_source)

math_ast = parse(math_source)
print("\nAST dump:")
print(dump(math_ast))

print("\n" + "=" * 60)
print("PARSING main.pine")
print("=" * 60)

with open("src/main.pine") as f:
    main_source = f.read()

print("\nSource:")
print(main_source)

main_ast = parse(main_source)
print("\nAST dump:")
print(dump(main_ast))

print("\n" + "=" * 60)
print("AST NODE TYPES")
print("=" * 60)

# Let's understand the AST node structure better
print("\nmath_ast type:", type(math_ast))
print("math_ast attributes:", dir(math_ast))

if hasattr(math_ast, 'body'):
    print("\nmath_ast.body:", math_ast.body)
    for i, node in enumerate(math_ast.body):
        print(f"\n  Node {i}: {type(node).__name__}")
        print(f"    Attributes: {[a for a in dir(node) if not a.startswith('_')]}")

print("\n" + "=" * 60)
print("TESTING UNPARSE")
print("=" * 60)

# Verify we can round-trip
print("\nUnparsed math_utils.pine:")
print(unparse(math_ast))

print("\nUnparsed main.pine:")
print(unparse(main_ast))

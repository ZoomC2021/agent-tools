"""Tests for string utility functions."""

import pytest
from tiny_python_app.strings import to_snake_case


def test_to_snake_case_pascal_case():
    """Convert PascalCase to snake_case."""
    assert to_snake_case("HelloWorld") == "hello_world"


def test_to_snake_case_camel_case():
    """Convert camelCase to snake_case."""
    assert to_snake_case("helloWorld") == "hello_world"


def test_to_snake_case_kebab_case():
    """Convert kebab-case to snake_case."""
    assert to_snake_case("hello-world") == "hello_world"


def test_to_snake_case_with_spaces():
    """Convert space-separated to snake_case."""
    assert to_snake_case("hello world") == "hello_world"


def test_to_snake_case_consecutive_uppercase():
    """Handle consecutive uppercase letters (acronyms)."""
    assert to_snake_case("HelloWorldURL") == "hello_world_url"
    assert to_snake_case("XMLHttpRequest") == "xml_http_request"


def test_to_snake_case_already_snake_case():
    """Handle already snake_case strings."""
    assert to_snake_case("hello_world") == "hello_world"


def test_to_snake_case_single_word():
    """Handle single word."""
    assert to_snake_case("hello") == "hello"
    assert to_snake_case("Hello") == "hello"

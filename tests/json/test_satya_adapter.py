"""
Test Satya adapter compatibility with fastjsonschema.
"""

from __future__ import annotations

import pytest

from poetry.json.satya_adapter import JsonSchemaValueException
from poetry.json.satya_adapter import compile
from poetry.json.satya_adapter import validate


def test_simple_string_validation() -> None:
    """Test basic string type validation"""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    # Valid data
    valid_data = {"name": "John"}
    validate(schema, valid_data)  # Should not raise

    # Invalid data - missing required field
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {})

    # Invalid data - wrong type
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"name": 123})


def test_integer_validation() -> None:
    """Test integer type and range validation"""
    schema = {
        "type": "object",
        "properties": {"age": {"type": "integer", "minimum": 0, "maximum": 150}},
        "required": ["age"],
    }

    # Valid data
    validate(schema, {"age": 30})
    validate(schema, {"age": 0})
    validate(schema, {"age": 150})

    # Invalid - below minimum
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"age": -1})

    # Invalid - above maximum
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"age": 151})

    # Invalid - wrong type (bool should not count as int)
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"age": True})


def test_enum_validation() -> None:
    """Test enum constraint validation"""
    schema = {
        "type": "object",
        "properties": {
            "priority": {"enum": ["primary", "supplemental", "explicit"]}
        },
    }

    # Valid values
    validate(schema, {"priority": "primary"})
    validate(schema, {"priority": "supplemental"})
    validate(schema, {"priority": "explicit"})

    # Invalid value
    with pytest.raises(JsonSchemaValueException) as exc:
        validate(schema, {"priority": "invalid"})
    assert "must be one of" in str(exc.value)


def test_array_validation() -> None:
    """Test array type validation"""
    schema = {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
    }

    # Valid array
    validate(schema, {"tags": ["python", "poetry", "packaging"]})
    validate(schema, {"tags": []})

    # Invalid - items not strings
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"tags": [1, 2, 3]})


def test_array_min_items() -> None:
    """Test array minItems constraint"""
    schema = {
        "type": "array",
        "minItems": 1,
        "items": {"type": "string"},
    }

    # Valid
    validate(schema, ["item1"])
    validate(schema, ["item1", "item2"])

    # Invalid - empty array
    with pytest.raises(JsonSchemaValueException) as exc:
        validate(schema, [])
    assert "at least" in str(exc.value)


def test_compile_reuse() -> None:
    """Test that compiled validator can be reused (important for performance)"""
    schema = {
        "type": "object",
        "properties": {"version": {"type": "string"}},
        "required": ["version"],
    }

    validator = compile(schema)

    # Validate multiple times with same validator
    for i in range(100):
        validator({"version": f"1.{i}.0"})


def test_poetry_repository_schema() -> None:
    """Test Poetry repository schema validation"""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "priority": {"enum": ["primary", "supplemental", "explicit"]},
        },
        "required": ["name"],
    }

    # Valid repository config
    validate(
        schema, {"name": "pypi", "url": "https://pypi.org/simple", "priority": "primary"}
    )

    # Missing required field
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"url": "https://pypi.org/simple"})

    # Invalid priority enum
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"name": "pypi", "priority": "invalid"})


def test_poetry_dependency_schema() -> None:
    """Test Poetry dependency schema validation (simplified)"""
    schema = {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "python": {"type": "string"},
            "markers": {"type": "string"},
            "optional": {"type": "boolean"},
            "extras": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["version"],
    }

    # Valid long-form dependency
    validate(
        schema,
        {
            "version": "^2.0",
            "python": "^3.8",
            "markers": "sys_platform == 'linux'",
            "optional": False,
            "extras": ["security", "speedups"],
        },
    )

    # Missing required version
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"python": "^3.8"})


def test_nested_object_validation() -> None:
    """Test validation of nested objects"""
    schema = {
        "type": "object",
        "properties": {
            "tool": {
                "type": "object",
                "properties": {"poetry": {"type": "object", "properties": {"name": {"type": "string"}}}},
            }
        },
    }

    # Valid nested structure
    validate(schema, {"tool": {"poetry": {"name": "my-package"}}})

    # Invalid - wrong type in nested property
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"tool": {"poetry": {"name": 123}}})


def test_pattern_properties() -> None:
    """Test pattern properties validation (used in Poetry dependencies)"""
    schema = {
        "type": "object",
        "patternProperties": {"^[a-zA-Z-_.0-9]+$": {"type": "string"}},
    }

    # Valid - keys match pattern, values are strings
    validate(schema, {"package-name": "^1.0", "other_package": ">=2.0"})

    # Invalid - values not strings
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"package": 123})


def test_string_length_constraints() -> None:
    """Test string minLength and maxLength"""
    schema = {"type": "string", "minLength": 3, "maxLength": 10}

    # Valid
    validate(schema, "hello")
    validate(schema, "abc")
    validate(schema, "1234567890")

    # Too short
    with pytest.raises(JsonSchemaValueException):
        validate(schema, "ab")

    # Too long
    with pytest.raises(JsonSchemaValueException):
        validate(schema, "12345678901")


def test_boolean_validation() -> None:
    """Test boolean type validation"""
    schema = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}

    # Valid
    validate(schema, {"enabled": True})
    validate(schema, {"enabled": False})

    # Invalid - 1 and 0 should not be accepted as booleans
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"enabled": 1})


def test_error_message_format() -> None:
    """Test that error messages follow fastjsonschema format"""
    schema = {"type": "string"}

    try:
        validate(schema, 123)
        pytest.fail("Should have raised JsonSchemaValueException")
    except JsonSchemaValueException as e:
        # Should have a message attribute like fastjsonschema
        assert hasattr(e, "message")
        assert "must be string" in e.message


def test_exception_compatibility() -> None:
    """Test that JsonSchemaValueException is compatible"""
    schema = {"type": "object", "required": ["field"]}

    with pytest.raises(JsonSchemaValueException) as exc_info:
        validate(schema, {})

    exc = exc_info.value
    # Should be a proper Exception with message
    assert isinstance(exc, Exception)
    assert hasattr(exc, "message")
    assert "required" in exc.message.lower()


def test_object_with_multiple_required_fields() -> None:
    """Test object with multiple required fields"""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["name", "version"],
    }

    # Valid - all required fields present
    validate(schema, {"name": "pkg", "version": "1.0.0", "description": "A package"})

    # Valid - optional field missing
    validate(schema, {"name": "pkg", "version": "1.0.0"})

    # Invalid - missing version
    with pytest.raises(JsonSchemaValueException):
        validate(schema, {"name": "pkg"})


def test_real_poetry_source_validation() -> None:
    """Test with real Poetry source configuration structure"""
    # This matches the actual schema in poetry.json
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "url": {"type": "string"},
            "priority": {"enum": ["primary", "supplemental", "explicit"]},
        },
    }

    # Valid complete source
    validate(
        schema,
        {
            "name": "private-repo",
            "url": "https://private.pypi.org/simple",
            "priority": "supplemental",
        },
    )

    # Valid minimal source (only required fields)
    validate(schema, {"name": "pypi"})

    # Invalid - missing required name
    with pytest.raises(JsonSchemaValueException) as exc:
        validate(schema, {"url": "https://example.com"})
    assert "name" in str(exc.value)
    assert "required" in str(exc.value)

    # Invalid - bad priority enum value
    with pytest.raises(JsonSchemaValueException) as exc:
        validate(schema, {"name": "repo", "priority": "high"})
    assert "must be one of" in str(exc.value)

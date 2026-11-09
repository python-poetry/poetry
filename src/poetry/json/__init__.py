from __future__ import annotations

import json

from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING
from typing import Any

import fastjsonschema

from fastjsonschema.exceptions import JsonSchemaValueException


if TYPE_CHECKING:
    from collections.abc import Callable


@cache
def _get_validator_and_properties() -> tuple[
    Callable[[dict[str, Any]], dict[str, Any]], frozenset[str]
]:
    schema = json.loads(
        (files(__package__) / "schemas" / "poetry.json").read_text(encoding="utf-8")
    )

    validator: Callable[[dict[str, Any]], dict[str, Any]] = fastjsonschema.compile(
        schema
    )

    core_schema = json.loads(
        (files("poetry.core") / "json" / "schemas" / "poetry-schema.json").read_text(
            encoding="utf-8"
        )
    )

    properties = frozenset(schema["properties"]) | frozenset(core_schema["properties"])
    return validator, properties


def validate_object(obj: dict[str, Any]) -> list[str]:
    validate, properties = _get_validator_and_properties()

    errors = []
    try:
        validate(obj)
    except JsonSchemaValueException as e:
        errors = [e.message]

    additional_properties = obj.keys() - properties
    for key in additional_properties:
        errors.append(f"Additional properties are not allowed ('{key}' was unexpected)")

    return errors

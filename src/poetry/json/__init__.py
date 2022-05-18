from __future__ import annotations

import json
import os

from typing import Any

import jsonschema


SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class ValidationError(ValueError):

    pass


def validate_object(obj: dict[str, Any], schema_name: str) -> list[str]:
    schema = os.path.join(SCHEMA_DIR, f"{schema_name}.json")

    if not os.path.exists(schema):
        raise ValueError(f"Schema {schema_name} does not exist.")

    with open(schema, encoding="utf-8") as f:
        schema = json.loads(f.read())

    validator = jsonschema.Draft7Validator(schema)
    validation_errors = sorted(
        validator.iter_errors(obj),
        key=lambda e: e.path,  # type: ignore[no-any-return]
    )

    errors = []

    for error in validation_errors:
        message = error.message
        if error.path:
            path = ".".join(str(x) for x in error.absolute_path)
            message = f"[{path}] {message}"

        errors.append(message)

    return errors

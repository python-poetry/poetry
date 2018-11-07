import json
import os

import jsonschema

from typing import List

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class ValidationError(ValueError):

    pass


def validate_object(obj, schema_name):  # type: (dict, str) -> List[str]
    schema = os.path.join(SCHEMA_DIR, "{}.json".format(schema_name))

    if not os.path.exists(schema):
        raise ValueError("Schema {} does not exist.".format(schema_name))

    with open(schema) as f:
        schema = json.loads(f.read())

    validator = jsonschema.Draft7Validator(schema)
    validation_errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)

    errors = []

    for error in validation_errors:
        message = error.message
        if error.path:
            message = "[{}] {}".format(".".join(error.path), message)

        errors.append(message)

    return errors

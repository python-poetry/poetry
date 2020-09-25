import json
import os
import pkgutil

from io import open
from typing import List

import jsonschema


class ValidationError(ValueError):

    pass


def validate_object(obj, schema_name):  # type: (dict, str) -> List[str]

    # 'poetry.json.schemas' is not an acceptable package (it is a namespace
    # package since it does not contain an '__init__.py' initializer). So we
    # use 'poetry.json' and the rest is part of the resource name.
    schema_resource_name = "schemas/{}.json".format(schema_name)

    schema_binary = pkgutil.get_data("poetry.json", schema_resource_name)
    if schema_binary is None:
        raise ValueError("Schema {} does not exist.".format(schema_name))

    schema = json.loads(schema_binary)

    validator = jsonschema.Draft7Validator(schema)
    validation_errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)

    errors = []

    for error in validation_errors:
        message = error.message
        if error.path:
            message = "[{}] {}".format(
                ".".join(str(x) for x in error.absolute_path), message
            )

        errors.append(message)

    return errors

import json
import os

import jsonschema

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class ValidationError(ValueError):

    pass


def validate_object(obj, schema_name):  # type: (dict, str) -> None
    schema = os.path.join(SCHEMA_DIR, "{}.json".format(schema_name))

    if not os.path.exists(schema):
        raise ValueError("Schema {} does not exist.".format(schema_name))

    with open(schema) as f:
        schema = json.loads(f.read())

    try:
        jsonschema.validate(obj, schema)
    except jsonschema.ValidationError as e:
        message = e.message
        if e.path:
            message = "[{}] {}".format(".".join(e.path), message)

        raise ValidationError(message)

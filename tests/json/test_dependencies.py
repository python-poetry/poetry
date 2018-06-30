import json
from pathlib import Path
import pytest
import jsonschema


PACKAGE_ROOT = Path(__file__).parent.parent.parent / "poetry"
MIN_CONFIG = {"name": "", "version": "", "description": ""}


@pytest.fixture
def schema():
    schema = PACKAGE_ROOT / "json" / "schemas" / "poetry-schema.json"
    with schema.open() as f:
        schema = json.loads(f.read())
    return schema


@pytest.mark.parametrize(
    "dependencies,expectation",
    [
        ({"dependencies": {"python": "", "a": {"path": "../b"}}}),
        ({"dev-dependencies": {"a": {"path": "../b"}}}),
    ],
)
def test_path_deps(dependencies, expectation, schema):
    config = {**MIN_CONFIG, **dependencies}
    # validate() either returns None(valid) or raises(invalid config or schema)
    assert jsonschema.validate(config, schema) is None

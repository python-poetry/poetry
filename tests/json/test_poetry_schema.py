import pytest

from poetry.json import validate_object


@pytest.fixture
def base_object():
    return {
        "name": "myapp",
        "version": "1.0.0",
        "description": "Some description.",
        "dependencies": {"python": "^3.6"},
        "dev-dependencies": {},
    }


def test_path_dependencies(base_object):
    base_object["dependencies"].update({"foo": {"path": "../foo"}})
    base_object["dev-dependencies"].update({"foo": {"path": "../foo"}})

    assert len(validate_object(base_object, "poetry-schema")) == 0

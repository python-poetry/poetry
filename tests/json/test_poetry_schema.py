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


@pytest.fixture
def multi_url_object():
    return {
        "name": "myapp",
        "version": "1.0.0",
        "description": "Some description.",
        "dependencies": {
            "python": [
                {
                    "url": "https://download.pytorch.org/whl/cpu/torch-1.4.0%2Bcpu-cp37-cp37m-linux_x86_64.whl",
                    "platform": "linux",
                },
                {"path": "../foo", "platform": "darwin"},
            ]
        },
        "dev-dependencies": {},
    }


def test_path_dependencies(base_object):
    base_object["dependencies"].update({"foo": {"path": "../foo"}})
    base_object["dev-dependencies"].update({"foo": {"path": "../foo"}})

    assert len(validate_object(base_object, "poetry-schema")) == 0


def test_multi_url_dependencies(multi_url_object):
    assert len(validate_object(multi_url_object, "poetry-schema")) == 0

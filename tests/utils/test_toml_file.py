import pytest

from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile


@pytest.fixture()
def fixture():
    return Path(__file__).parent / "fixtures" / "test.toml"


def test_toml_file(fixture):
    f = TomlFile(fixture)

    content = f.read()

    assert content["title"] == "TOML Example"

    assert content["owner"]["name"] == "Tom Preston-Werner"
    assert isinstance(content["owner"], dict)

    assert isinstance(content["database"]["ports"], list)
    assert content["database"]["ports"] == [8001, 8001, 8002]
    assert content["database"]["connection_max"] == 5000
    assert content["database"]["enabled"]

    servers = content["servers"]
    assert len(servers) == 2
    alpha = servers["alpha"]
    assert len(alpha) == 2
    assert alpha["ip"] == "10.0.0.1"
    assert alpha["dc"] == "eqdc10"
    beta = servers["beta"]
    assert len(beta) == 2
    assert beta["ip"] == "10.0.0.2"
    assert beta["dc"] == "eqdc10"

    clients = content["clients"]
    assert len(clients["data"]) == 2
    assert clients["data"] == [["gamma", "delta"], [1, 2]]
    assert clients["hosts"] == ["alpha", "omega"]
    assert clients["str_multiline"] == "Roses are red\nViolets are blue"

    fruits = content["fruit"]
    assert len(fruits) == 2
    apple = fruits[0]
    assert len(apple) == 3
    banana = fruits[1]
    assert len(banana["variety"][0]["points"]) == 3


def test_pyproject_parsing(fixture):
    f = TomlFile(fixture.with_name("pyproject.toml"))

    content = f.read()

    assert "dependencies" in content["tool"]["poetry"]
    assert content["tool"]["poetry"]["dependencies"]["python"] == "^3.6"

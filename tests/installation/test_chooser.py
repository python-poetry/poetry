import re

import pytest

from packaging.tags import Tag
from poetry.core.packages.package import Package
from poetry.installation.chooser import Chooser
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pool import Pool
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv


JSON_FIXTURES = (
    Path(__file__).parent.parent / "repositories" / "fixtures" / "pypi.org" / "json"
)

LEGACY_FIXTURES = Path(__file__).parent.parent / "repositories" / "fixtures" / "legacy"


@pytest.fixture()
def env():
    return MockEnv(
        supported_tags=[
            Tag("cp37", "cp37", "macosx_10_15_x86_64"),
            Tag("py3", "none", "any"),
        ]
    )


@pytest.fixture()
def mock_pypi(http):
    def callback(request, uri, headers):
        parts = uri.rsplit("/")

        name = parts[-3]
        version = parts[-2]

        fixture = JSON_FIXTURES / name / (version + ".json")
        if not fixture.exists():
            fixture = JSON_FIXTURES / (name + ".json")

        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET, re.compile("^https://pypi.org/(.+?)/(.+?)/json$"), body=callback,
    )


@pytest.fixture()
def mock_legacy(http):
    def callback(request, uri, headers):
        parts = uri.rsplit("/")
        name = parts[-2]

        fixture = LEGACY_FIXTURES / (name + ".html")

        with fixture.open(encoding="utf-8") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET, re.compile("^https://foo.bar/simple/(.+?)$"), body=callback,
    )


@pytest.fixture()
def pool():
    pool = Pool()

    pool.add_repository(PyPiRepository(disable_cache=True))
    pool.add_repository(
        LegacyRepository("foo", "https://foo.bar/simple/", disable_cache=True)
    )

    return pool


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_universal_wheel_link_if_available(
    env, mock_pypi, mock_legacy, source_type, pool
):
    chooser = Chooser(pool, env)

    package = Package("pytest", "3.5.0")
    if source_type == "legacy":
        package.source_type = "legacy"
        package.source_reference = "foo"
        package.source_url = "https://foo.bar/simple/"

    link = chooser.choose_for(package)

    assert "pytest-3.5.0-py2.py3-none-any.whl" == link.filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_specific_python_universal_wheel_link_if_available(
    env, mock_pypi, mock_legacy, source_type, pool
):
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    if source_type == "legacy":
        package.source_type = "legacy"
        package.source_reference = "foo"
        package.source_url = "https://foo.bar/simple/"

    link = chooser.choose_for(package)

    assert "isort-4.3.4-py3-none-any.whl" == link.filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_system_specific_wheel_link_if_available(
    mock_pypi, mock_legacy, source_type, pool
):
    env = MockEnv(
        supported_tags=[Tag("cp37", "cp37m", "win32"), Tag("py3", "none", "any")]
    )
    chooser = Chooser(pool, env)

    package = Package("pyyaml", "3.13.0")
    if source_type == "legacy":
        package.source_type = "legacy"
        package.source_reference = "foo"
        package.source_url = "https://foo.bar/simple/"

    link = chooser.choose_for(package)

    assert "PyYAML-3.13-cp37-cp37m-win32.whl" == link.filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_sdist_if_no_compatible_wheel_link_is_available(
    env, mock_pypi, mock_legacy, source_type, pool,
):
    chooser = Chooser(pool, env)

    package = Package("pyyaml", "3.13.0")
    if source_type == "legacy":
        package.source_type = "legacy"
        package.source_reference = "foo"
        package.source_url = "https://foo.bar/simple/"

    link = chooser.choose_for(package)

    assert "PyYAML-3.13.tar.gz" == link.filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_distributions_that_match_the_package_hashes(
    env, mock_pypi, mock_legacy, source_type, pool,
):
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    package.files = [
        {
            "hash": "sha256:b9c40e9750f3d77e6e4d441d8b0266cf555e7cdabdcff33c4fd06366ca761ef8",
            "filename": "isort-4.3.4.tar.gz",
        }
    ]
    if source_type == "legacy":
        package.source_type = "legacy"
        package.source_reference = "foo"
        package.source_url = "https://foo.bar/simple/"

    link = chooser.choose_for(package)

    assert "isort-4.3.4.tar.gz" == link.filename

from __future__ import annotations

import base64
import re
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.dependency import Dependency

from poetry.factory import Factory
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.link_sources.html import SimpleRepositoryPage


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

if TYPE_CHECKING:
    import httpretty

    from _pytest.monkeypatch import MonkeyPatch

    from poetry.config.config import Config


@pytest.fixture(autouse=True)
def _use_simple_keyring(with_simple_keyring: None) -> None:
    pass


class MockRepository(LegacyRepository):
    FIXTURES = Path(__file__).parent / "fixtures" / "legacy"

    def __init__(self) -> None:
        super().__init__("legacy", url="http://legacy.foo.bar", disable_cache=True)

    def _get_page(self, endpoint: str) -> SimpleRepositoryPage | None:
        parts = endpoint.split("/")
        name = parts[1]

        fixture = self.FIXTURES / (name + ".html")
        if not fixture.exists():
            return None

        with fixture.open(encoding="utf-8") as f:
            return SimpleRepositoryPage(self._url + endpoint, f.read())

    def _download(self, url: str, dest: Path) -> None:
        filename = urlparse.urlparse(url).path.rsplit("/")[-1]
        filepath = self.FIXTURES.parent / "pypi.org" / "dists" / filename

        shutil.copyfile(str(filepath), dest)


def test_packages_property_returns_empty_list() -> None:
    repo = MockRepository()
    repo._packages = [repo.package("jupyter", Version.parse("1.0.0"))]

    assert repo.packages == []


def test_page_relative_links_path_are_correct() -> None:
    repo = MockRepository()

    page = repo.get_page("/relative")
    assert page is not None

    for link in page.links:
        assert link.netloc == "legacy.foo.bar"
        assert link.path.startswith("/relative/poetry")


def test_page_absolute_links_path_are_correct() -> None:
    repo = MockRepository()

    page = repo.get_page("/absolute")
    assert page is not None

    for link in page.links:
        assert link.netloc == "files.pythonhosted.org"
        assert link.path.startswith("/packages/")


def test_page_clean_link() -> None:
    repo = MockRepository()

    page = repo.get_page("/relative")
    assert page is not None

    cleaned = page.clean_link('https://legacy.foo.bar/test /the"/cleaning\0')
    assert cleaned == "https://legacy.foo.bar/test%20/the%22/cleaning%00"


def test_page_invalid_version_link() -> None:
    repo = MockRepository()

    page = repo.get_page("/invalid-version")
    assert page is not None

    links = list(page.links)
    assert len(links) == 1

    versions = list(page.versions(canonicalize_name("poetry")))
    assert len(versions) == 1
    assert versions[0].to_string() == "0.1.0"

    packages = list(page.packages)
    assert len(packages) == 1
    assert packages[0].name == "poetry"
    assert packages[0].version.to_string() == "0.1.0"


def test_sdist_format_support() -> None:
    repo = MockRepository()
    page = repo.get_page("/relative")
    assert page is not None
    bz2_links = list(filter(lambda link: link.ext == ".tar.bz2", page.links))
    assert len(bz2_links) == 1
    assert bz2_links[0].filename == "poetry-0.1.1.tar.bz2"


def test_missing_version() -> None:
    repo = MockRepository()

    with pytest.raises(PackageNotFound):
        repo._get_release_info(
            canonicalize_name("missing_version"), Version.parse("1.1.0")
        )


def test_get_package_information_fallback_read_setup() -> None:
    repo = MockRepository()

    package = repo.package("jupyter", Version.parse("1.0.0"))

    assert package.source_type == "legacy"
    assert package.source_reference == repo.name
    assert package.source_url == repo.url
    assert package.name == "jupyter"
    assert package.version.text == "1.0.0"
    assert (
        package.description
        == "Jupyter metapackage. Install all the Jupyter components in one go."
    )


def test_get_package_information_skips_dependencies_with_invalid_constraints() -> None:
    repo = MockRepository()

    package = repo.package("python-language-server", Version.parse("0.21.2"))

    assert package.name == "python-language-server"
    assert package.version.text == "0.21.2"
    assert (
        package.description == "Python Language Server for the Language Server Protocol"
    )

    assert len(package.requires) == 25
    assert sorted(
        (r for r in package.requires if not r.is_optional()), key=lambda r: r.name
    ) == [
        Dependency("configparser", "*"),
        Dependency("future", ">=0.14.0"),
        Dependency("futures", "*"),
        Dependency("jedi", ">=0.12"),
        Dependency("pluggy", "*"),
        Dependency("python-jsonrpc-server", "*"),
    ]

    all_extra = package.extras["all"]

    # rope>-0.10.5 should be discarded
    assert sorted(all_extra, key=lambda r: r.name) == [
        Dependency("autopep8", "*"),
        Dependency("mccabe", "*"),
        Dependency("pycodestyle", "*"),
        Dependency("pydocstyle", ">=2.0.0"),
        Dependency("pyflakes", ">=1.6.0"),
        Dependency("yapf", "*"),
    ]


def test_package_not_canonicalized() -> None:
    repo = MockRepository()

    package = repo.package("discord.py", Version.parse("2.0.0"))

    assert package.name == "discord-py"
    assert package.pretty_name == "discord.py"


def test_find_packages_no_prereleases() -> None:
    repo = MockRepository()

    packages = repo.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1

    assert packages[0].source_type == "legacy"
    assert packages[0].source_reference == repo.name
    assert packages[0].source_url == repo.url


@pytest.mark.parametrize(
    ["constraint", "count"], [("*", 1), (">=1", 0), (">=19.0.0a0", 1)]
)
def test_find_packages_only_prereleases(constraint: str, count: int) -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert len(packages) == count

    if count >= 0:
        for package in packages:
            assert package.source_type == "legacy"
            assert package.source_reference == repo.name
            assert package.source_url == repo.url


def test_find_packages_only_prereleases_empty_when_not_any() -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", ">=1"))

    assert len(packages) == 0


@pytest.mark.parametrize(
    ["constraint", "expected"],
    [
        # yanked 21.11b0 is ignored except for pinned version
        ("*", ["19.10b0"]),
        (">=19.0a0", ["19.10b0"]),
        (">=20.0a0", []),
        (">=21.11b0", []),
        ("==21.11b0", ["21.11b0"]),
    ],
)
def test_find_packages_yanked(constraint: str, expected: list[str]) -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert [str(p.version) for p in packages] == expected


def test_get_package_information_chooses_correct_distribution() -> None:
    repo = MockRepository()

    package = repo.package("isort", Version.parse("4.3.4"))

    assert package.name == "isort"
    assert package.version.text == "4.3.4"

    assert package.requires == [Dependency("futures", "*")]
    futures_dep = package.requires[0]
    assert futures_dep.python_versions == "~2.7"


def test_get_package_information_includes_python_requires() -> None:
    repo = MockRepository()

    package = repo.package("futures", Version.parse("3.2.0"))

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_information_sets_appropriate_python_versions_if_wheels_only() -> (
    None
):
    repo = MockRepository()

    package = repo.package("futures", Version.parse("3.2.0"))

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_from_both_py2_and_py3_specific_wheels() -> None:
    repo = MockRepository()

    package = repo.package("ipython", Version.parse("5.7.0"))

    assert package.name == "ipython"
    assert package.version.text == "5.7.0"
    assert package.python_versions == "*"
    assert len(package.requires) == 41

    expected = [
        Dependency("appnope", "*"),
        Dependency("backports.shutil-get-terminal-size", "*"),
        Dependency("colorama", "*"),
        Dependency("decorator", "*"),
        Dependency("pathlib2", "*"),
        Dependency("pexpect", "*"),
        Dependency("pickleshare", "*"),
        Dependency("prompt-toolkit", ">=1.0.4,<2.0.0"),
        Dependency("pygments", "*"),
        Dependency("setuptools", ">=18.5"),
        Dependency("simplegeneric", ">0.8"),
        Dependency("traitlets", ">=4.2"),
        Dependency("win-unicode-console", ">=0.5"),
    ]
    required = [r for r in package.requires if not r.is_optional()]
    assert required == expected

    assert str(required[1].marker) == 'python_version == "2.7"'
    assert (
        str(required[12].marker) == 'sys_platform == "win32" and python_version < "3.6"'
    )
    assert (
        str(required[4].marker) == 'python_version == "2.7" or python_version == "3.3"'
    )
    assert str(required[5].marker) == 'sys_platform != "win32"'


def test_get_package_from_both_py2_and_py3_specific_wheels_python_constraint() -> None:
    repo = MockRepository()

    package = repo.package("poetry-test-py2-py3-metadata-merge", Version.parse("0.1.0"))

    assert package.name == "poetry-test-py2-py3-metadata-merge"
    assert package.version.text == "0.1.0"
    assert package.python_versions == ">=2.7,<2.8 || >=3.7,<4.0"


def test_get_package_with_dist_and_universal_py3_wheel() -> None:
    repo = MockRepository()

    package = repo.package("ipython", Version.parse("7.5.0"))

    assert package.name == "ipython"
    assert package.version.text == "7.5.0"
    assert package.python_versions == ">=3.5"

    expected = [
        Dependency("appnope", "*"),
        Dependency("backcall", "*"),
        Dependency("colorama", "*"),
        Dependency("decorator", "*"),
        Dependency("jedi", ">=0.10"),
        Dependency("pexpect", "*"),
        Dependency("pickleshare", "*"),
        Dependency("prompt-toolkit", ">=2.0.0,<2.1.0"),
        Dependency("pygments", "*"),
        Dependency("setuptools", ">=18.5"),
        Dependency("traitlets", ">=4.2"),
        Dependency("typing", "*"),
        Dependency("win-unicode-console", ">=0.5"),
    ]
    required = [r for r in package.requires if not r.is_optional()]
    assert sorted(required, key=lambda dep: dep.name) == expected


def test_get_package_retrieves_non_sha256_hashes() -> None:
    repo = MockRepository()

    package = repo.package("ipython", Version.parse("7.5.0"))

    expected = [
        {
            "file": "ipython-7.5.0-py3-none-any.whl",
            "hash": "sha256:78aea20b7991823f6a32d55f4e963a61590820e43f666ad95ad07c7f0c704efa",  # noqa: E501
        },
        {
            "file": "ipython-7.5.0.tar.gz",
            "hash": "sha256:e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26",  # noqa: E501
        },
    ]

    assert package.files == expected


def test_get_package_retrieves_non_sha256_hashes_mismatching_known_hash() -> None:
    repo = MockRepository()

    package = repo.package("ipython", Version.parse("5.7.0"))

    expected = [
        {
            "file": "ipython-5.7.0-py2-none-any.whl",
            "hash": "md5:a10a802ef98da741cd6f4f6289d47ba7",
        },
        {
            "file": "ipython-5.7.0-py3-none-any.whl",
            "hash": "sha256:fc0464e68f9c65cd8c453474b4175432cc29ecb6c83775baedf6dbfcee9275ab",  # noqa: E501
        },
        {
            "file": "ipython-5.7.0.tar.gz",
            "hash": "sha256:8db43a7fb7619037c98626613ff08d03dda9d5d12c84814a4504c78c0da8323c",  # noqa: E501
        },
    ]

    assert package.files == expected


def test_get_package_retrieves_packages_with_no_hashes() -> None:
    repo = MockRepository()

    package = repo.package("jupyter", Version.parse("1.0.0"))

    assert [
        {
            "file": "jupyter-1.0.0.tar.gz",
            "hash": "sha256:d9dc4b3318f310e34c82951ea5d6683f67bed7def4b259fafbfe4f1beb1d8e5f",  # noqa: E501
        }
    ] == package.files


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "Broken regex dependency. Use 21.11b1 instead."),
    ],
)
def test_package_yanked(
    package_name: str, version: str, yanked: bool, yanked_reason: str
) -> None:
    repo = MockRepository()

    package = repo.package(package_name, Version.parse(version))

    assert package.name == package_name
    assert str(package.version) == version
    assert package.yanked is yanked
    assert package.yanked_reason == yanked_reason


def test_package_partial_yank():
    class SpecialMockRepository(MockRepository):
        def _get_page(self, endpoint: str) -> SimpleRepositoryPage | None:
            return super()._get_page(f"/{endpoint.strip('/')}_partial_yank/")

    repo = MockRepository()
    package = repo.package("futures", Version.parse("3.2.0"))
    assert len(package.files) == 2

    repo = SpecialMockRepository()
    package = repo.package("futures", Version.parse("3.2.0"))
    assert len(package.files) == 1
    assert package.files[0]["file"].endswith(".tar.gz")


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "Broken regex dependency. Use 21.11b1 instead."),
    ],
)
def test_find_links_for_package_yanked(
    package_name: str, version: str, yanked: bool, yanked_reason: str
) -> None:
    repo = MockRepository()

    package = repo.package(package_name, Version.parse(version))
    links = repo.find_links_for_package(package)

    assert len(links) == 1
    for link in links:
        assert link.yanked == yanked
        assert link.yanked_reason == yanked_reason


class MockHttpRepository(LegacyRepository):
    def __init__(
        self, endpoint_responses: dict, http: type[httpretty.httpretty]
    ) -> None:
        base_url = "http://legacy.foo.bar"
        super().__init__("legacy", url=base_url, disable_cache=True)

        for endpoint, response in endpoint_responses.items():
            url = base_url + endpoint
            http.register_uri(http.GET, url, status=response)


def test_get_200_returns_page(http: type[httpretty.httpretty]) -> None:
    repo = MockHttpRepository({"/foo": 200}, http)

    assert repo.get_page("/foo")


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_get_40x_and_returns_none(
    http: type[httpretty.httpretty], status_code: int
) -> None:
    repo = MockHttpRepository({"/foo": status_code}, http)

    assert repo.get_page("/foo") is None


def test_get_5xx_raises(http: type[httpretty.httpretty]) -> None:
    repo = MockHttpRepository({"/foo": 500}, http)

    with pytest.raises(RepositoryError):
        repo.get_page("/foo")


def test_get_redirected_response_url(
    http: type[httpretty.httpretty], monkeypatch: MonkeyPatch
) -> None:
    repo = MockHttpRepository({"/foo": 200}, http)
    redirect_url = "http://legacy.redirect.bar"

    def get_mock(
        url: str, raise_for_status: bool = True, timeout: int = 5
    ) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = redirect_url + "/foo"
        return response

    monkeypatch.setattr(repo.session, "get", get_mock)
    page = repo.get_page("/foo")
    assert page is not None
    assert page._url == "http://legacy.redirect.bar/foo/"


@pytest.mark.parametrize(
    ("repositories",),
    [
        ({},),
        # ensure path is respected
        ({"publish": {"url": "https://foo.bar/legacy"}},),
        # ensure path length does not give incorrect results
        ({"publish": {"url": "https://foo.bar/upload/legacy"}},),
    ],
)
def test_authenticator_with_implicit_repository_configuration(
    http: type[httpretty.httpretty],
    config: Config,
    repositories: dict[str, dict[str, str]],
) -> None:
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )

    config.merge(
        {
            "repositories": repositories,
            "http-basic": {
                "source": {"username": "foo", "password": "bar"},
                "publish": {"username": "baz", "password": "qux"},
            },
        }
    )

    repo = LegacyRepository(name="source", url="https://foo.bar/simple", config=config)
    repo.get_page("/foo")

    request = http.last_request()

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

from __future__ import annotations

import base64
import re

from typing import TYPE_CHECKING
from typing import Any

import pytest
import requests

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.utils.link import Link

from poetry.factory import Factory
from poetry.repositories.exceptions import PackageNotFoundError
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.legacy_repository import LegacyRepository


if TYPE_CHECKING:
    from collections.abc import Callable

    import responses

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from tests.repositories.fixtures.legacy import TestLegacyRepository
    from tests.types import DistributionHashGetter


@pytest.fixture(autouse=True)
def _use_simple_keyring(with_simple_keyring: None) -> None:
    pass


def test_page_relative_links_path_are_correct(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    page = repo.get_page("relative")
    assert page is not None

    for link in page.links:
        assert link.netloc == "legacy.foo.bar"
        assert link.path.startswith("/relative/poetry")


def test_page_absolute_links_path_are_correct(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    page = repo.get_page("absolute")
    assert page is not None

    for link in page.links:
        assert link.netloc == "files.pythonhosted.org"
        assert link.path.startswith("/packages/")


def test_page_clean_link(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository

    page = repo.get_page("relative")
    assert page is not None

    cleaned = page.clean_link('https://legacy.foo.bar/test /the"/cleaning\0')
    assert cleaned == "https://legacy.foo.bar/test%20/the%22/cleaning%00"


def test_page_invalid_version_link(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository

    page = repo.get_page("invalid-version")
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


def test_page_filters_out_invalid_package_names(
    legacy_repository_with_extra_packages: LegacyRepository,
    get_legacy_dist_url: Callable[[str], str],
    dist_hash_getter: DistributionHashGetter,
) -> None:
    repo = legacy_repository_with_extra_packages
    packages = repo.find_packages(Factory.create_dependency("pytest", "*"))
    assert len(packages) == 1
    assert packages[0].name == "pytest"
    assert packages[0].version == Version.parse("3.5.0")

    package = repo.package("pytest", Version.parse("3.5.0"))
    assert package.files == [
        {
            "file": filename,
            "hash": f"sha256:{dist_hash_getter(filename).sha256}",
            "url": get_legacy_dist_url(filename),
        }
        for filename in [
            f"{package.name}-{package.version}-py2.py3-none-any.whl",
            f"{package.name}-{package.version}.tar.gz",
        ]
    ]


def test_sdist_format_support(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository
    page = repo.get_page("relative")
    assert page is not None
    bz2_links = list(filter(lambda link: link.ext == ".tar.bz2", page.links))
    assert len(bz2_links) == 1
    assert bz2_links[0].filename == "poetry-0.1.1.tar.bz2"


def test_missing_version(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository

    with pytest.raises(PackageNotFoundError):
        repo._get_release_info(
            canonicalize_name("missing_version"), Version.parse("1.1.0")
        )


def test_get_package_information_fallback_read_setup(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

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


def test_get_package_information_pep_658(
    mocker: MockerFixture, legacy_repository: LegacyRepository
) -> None:
    repo = legacy_repository

    isort_package = repo.package("isort", Version.parse("4.3.4"))

    spy = mocker.spy(repo, "_get_info_from_metadata")

    try:
        package = repo.package("isort-metadata", Version.parse("4.3.4"))
    except FileNotFoundError:
        pytest.fail("Metadata was not successfully retrieved")
    else:
        assert spy.call_count > 0
        assert spy.spy_return is not None

        assert package.source_type == isort_package.source_type == "legacy"
        assert package.source_reference == isort_package.source_reference == repo.name
        assert package.source_url == isort_package.source_url == repo.url
        assert package.name == "isort-metadata"
        assert package.version.text == isort_package.version.text == "4.3.4"
        assert package.description == isort_package.description
        assert (
            package.requires == isort_package.requires == [Dependency("futures", "*")]
        )
        assert (
            str(package.python_constraint)
            == str(isort_package.python_constraint)
            == ">=2.7,<3.0.dev0 || >=3.4.dev0"
        )


def test_get_package_information_skips_dependencies_with_invalid_constraints(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

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

    all_extra = package.extras[canonicalize_name("all")]

    # rope>-0.10.5 should be discarded
    assert sorted(all_extra, key=lambda r: r.name) == [
        Dependency("autopep8", "*"),
        Dependency("mccabe", "*"),
        Dependency("pycodestyle", "*"),
        Dependency("pydocstyle", ">=2.0.0"),
        Dependency("pyflakes", ">=1.6.0"),
        Dependency("yapf", "*"),
    ]


def test_package_not_canonicalized(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository

    package = repo.package("discord.py", Version.parse("2.0.0"))

    assert package.name == "discord-py"
    assert package.pretty_name == "discord.py"


def test_find_packages_no_prereleases(legacy_repository: LegacyRepository) -> None:
    repo = legacy_repository

    packages = repo.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1

    assert packages[0].source_type == "legacy"
    assert packages[0].source_reference == repo.name
    assert packages[0].source_url == repo.url


@pytest.mark.parametrize(
    ["constraint", "count"], [("*", 1), (">=1", 1), ("<=18", 0), (">=19.0.0a0", 1)]
)
def test_find_packages_only_prereleases(
    constraint: str, count: int, legacy_repository: LegacyRepository
) -> None:
    repo = legacy_repository
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert len(packages) == count

    if count >= 0:
        for package in packages:
            assert package.source_type == "legacy"
            assert package.source_reference == repo.name
            assert package.source_url == repo.url


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
def test_find_packages_yanked(
    constraint: str, expected: list[str], legacy_repository: LegacyRepository
) -> None:
    repo = legacy_repository
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert [str(p.version) for p in packages] == expected


def test_get_package_information_chooses_correct_distribution(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package("isort", Version.parse("4.3.4"))

    assert package.name == "isort"
    assert package.version.text == "4.3.4"

    assert package.requires == [Dependency("futures", "*")]
    futures_dep = package.requires[0]
    assert futures_dep.python_versions == "~2.7"


def test_get_package_information_includes_python_requires(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package("futures", Version.parse("3.2.0"))

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_information_includes_files(
    legacy_repository: TestLegacyRepository,
    dist_hash_getter: DistributionHashGetter,
    get_legacy_dist_url: Callable[[str], str],
    get_legacy_dist_size_and_upload_time: Callable[
        [str], tuple[int | None, str | None]
    ],
) -> None:
    repo = legacy_repository

    package = repo.package("futures", Version.parse("3.2.0"))

    expected: list[dict[str, Any]] = [
        {
            "file": filename,
            "hash": f"sha256:{dist_hash_getter(filename).sha256}",
            "url": get_legacy_dist_url(filename),
        }
        for filename in [
            f"{package.name}-{package.version}-py2-none-any.whl",
            f"{package.name}-{package.version}.tar.gz",
        ]
    ]
    if repo.json:
        for file_info in expected:
            size, upload_time = get_legacy_dist_size_and_upload_time(file_info["file"])
            if size is not None:
                file_info["size"] = size
            if upload_time is not None:
                file_info["upload_time"] = upload_time

    assert package.files == expected


def test_get_package_information_sets_appropriate_python_versions_if_wheels_only(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package("futures", Version.parse("3.2.0"))

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_from_both_py2_and_py3_specific_wheels(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

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


def test_get_package_from_both_py2_and_py3_specific_wheels_python_constraint(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package("poetry-test-py2-py3-metadata-merge", Version.parse("0.1.0"))

    assert package.name == "poetry-test-py2-py3-metadata-merge"
    assert package.version.text == "0.1.0"
    assert package.python_versions == ">=2.7,<2.8 || >=3.7,<4.0"


def test_get_package_with_dist_and_universal_py3_wheel(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

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


def test_get_package_retrieves_non_sha256_hashes(
    legacy_repository: TestLegacyRepository,
    dist_hash_getter: DistributionHashGetter,
    get_legacy_dist_url: Callable[[str], str],
    get_legacy_dist_size_and_upload_time: Callable[
        [str], tuple[int | None, str | None]
    ],
) -> None:
    repo = legacy_repository

    package = repo.package("ipython", Version.parse("7.5.0"))

    expected: list[dict[str, Any]] = [
        {
            "file": filename,
            "hash": f"sha256:{dist_hash_getter(filename).sha256}",
            "url": get_legacy_dist_url(filename),
        }
        for filename in [
            f"{package.name}-{package.version}-py3-none-any.whl",
            f"{package.name}-{package.version}.tar.gz",
        ]
    ]
    if repo.json:
        for file_info in expected:
            size, upload_time = get_legacy_dist_size_and_upload_time(file_info["file"])
            if size is not None:
                file_info["size"] = size
            if upload_time is not None:
                file_info["upload_time"] = upload_time

    assert package.files == expected


def test_get_package_retrieves_non_sha256_hashes_mismatching_known_hash(
    legacy_repository: TestLegacyRepository,
    dist_hash_getter: DistributionHashGetter,
    get_legacy_dist_url: Callable[[str], str],
    get_legacy_dist_size_and_upload_time: Callable[
        [str], tuple[int | None, str | None]
    ],
) -> None:
    repo = legacy_repository

    package = repo.package("ipython", Version.parse("5.7.0"))

    expected: list[dict[str, Any]] = [
        {
            "file": "ipython-5.7.0-py2-none-any.whl",
            # in the links provided by the legacy repository, this file only has a md5 hash,
            # the sha256 is generated on the fly
            "hash": f"sha256:{dist_hash_getter('ipython-5.7.0-py2-none-any.whl').sha256}",
            "url": get_legacy_dist_url("ipython-5.7.0-py2-none-any.whl"),
        },
        {
            "file": "ipython-5.7.0-py3-none-any.whl",
            "hash": f"sha256:{dist_hash_getter('ipython-5.7.0-py3-none-any.whl').sha256}",
            "url": get_legacy_dist_url("ipython-5.7.0-py3-none-any.whl"),
        },
        {
            "file": "ipython-5.7.0.tar.gz",
            "hash": f"sha256:{dist_hash_getter('ipython-5.7.0.tar.gz').sha256}",
            "url": get_legacy_dist_url("ipython-5.7.0.tar.gz"),
        },
    ]
    if repo.json:
        for file_info in expected:
            size, upload_time = get_legacy_dist_size_and_upload_time(file_info["file"])
            if size is not None:
                file_info["size"] = size
            if upload_time is not None:
                file_info["upload_time"] = upload_time

    assert package.files == expected


def test_get_package_retrieves_packages_with_no_hashes(
    legacy_repository: LegacyRepository,
    dist_hash_getter: DistributionHashGetter,
    get_legacy_dist_url: Callable[[str], str],
) -> None:
    repo = legacy_repository

    package = repo.package("jupyter", Version.parse("1.0.0"))

    assert [
        {
            "file": filename,
            "hash": f"sha256:{dist_hash_getter(filename).sha256}",
            "url": get_legacy_dist_url(filename),
        }
        for filename in [
            f"{package.name}-{package.version}.tar.gz",
        ]
    ] == package.files


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "Broken regex dependency. Use 21.11b1 instead."),
    ],
)
def test_package_yanked(
    package_name: str,
    version: str,
    yanked: bool,
    yanked_reason: str,
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package(package_name, Version.parse(version))

    assert package.name == package_name
    assert str(package.version) == version
    assert package.yanked is yanked
    assert package.yanked_reason == yanked_reason


def test_package_partial_yank(
    legacy_repository_html: LegacyRepository,
    legacy_repository_partial_yank: LegacyRepository,
) -> None:
    repo = legacy_repository_html
    package = repo.package("futures", Version.parse("3.2.0"))
    assert len(package.files) == 2

    repo = legacy_repository_partial_yank
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
    package_name: str,
    version: str,
    yanked: bool,
    yanked_reason: str,
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository

    package = repo.package(package_name, Version.parse(version))
    links = repo.find_links_for_package(package)

    assert len(links) == 2
    for link in links:
        assert link.yanked == yanked
        assert link.yanked_reason == yanked_reason


def test_cached_or_downloaded_file_supports_trailing_slash(
    legacy_repository: LegacyRepository,
) -> None:
    repo = legacy_repository
    with repo._cached_or_downloaded_file(
        Link("https://files.pythonhosted.org/pytest-3.5.0-py2.py3-none-any.whl/")
    ) as filepath:
        assert filepath.name == "pytest-3.5.0-py2.py3-none-any.whl"


class MockHttpRepository(LegacyRepository):
    def __init__(
        self, endpoint_responses: dict[str, int], http: responses.RequestsMock
    ) -> None:
        base_url = "http://legacy.foo.bar"
        super().__init__("legacy", url=base_url, disable_cache=True)

        for endpoint, response in endpoint_responses.items():
            url = base_url + endpoint
            http.get(url, status=response)


def test_get_200_returns_page(http: responses.RequestsMock) -> None:
    repo = MockHttpRepository({"/foo/": 200}, http)

    _ = repo.get_page("foo")


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_get_40x_and_returns_none(
    http: responses.RequestsMock, status_code: int
) -> None:
    repo = MockHttpRepository({"/foo/": status_code}, http)

    with pytest.raises(PackageNotFoundError):
        repo.get_page("foo")


def test_get_5xx_raises(
    http: responses.RequestsMock, disable_http_status_force_list: None
) -> None:
    repo = MockHttpRepository({"/foo/": 500}, http)

    with pytest.raises(RepositoryError):
        repo.get_page("foo")


def test_get_redirected_response_url(
    http: responses.RequestsMock, monkeypatch: MonkeyPatch
) -> None:
    repo = MockHttpRepository({"/foo/": 200}, http)
    redirect_url = "http://legacy.redirect.bar"

    def get_mock(*args: Any, **kwargs: Any) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = redirect_url + "/foo"
        return response

    monkeypatch.setattr(repo.session, "get", get_mock)
    page = repo.get_page("foo")
    assert page is not None
    assert page._url == "http://legacy.redirect.bar/foo"


def test_get_page_prefers_json(http: responses.RequestsMock) -> None:
    repo = MockHttpRepository({"/foo/": 200}, http)

    _ = repo.get_page("foo")

    accepted = [
        item.strip()
        for item in http.calls[-1].request.headers.get("Accept", "").split(",")
    ]
    preferred = [item for item in accepted if "q=0" not in item.split(";")[-1]]

    assert preferred == ["application/vnd.pypi.simple.v1+json"]
    assert any("*/*" in item for item in accepted)


def test_root_page_prefers_json(http: responses.RequestsMock) -> None:
    repo = MockHttpRepository({"/": 200}, http)

    _ = repo.root_page

    accepted = [
        item.strip()
        for item in http.calls[-1].request.headers.get("Accept", "").split(",")
    ]
    preferred = [item for item in accepted if "q=0" not in item.split(";")[-1]]

    assert preferred == ["application/vnd.pypi.simple.v1+json"]
    assert any("*/*" in item for item in accepted)


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
    http: responses.RequestsMock,
    config: Config,
    repositories: dict[str, dict[str, str]],
) -> None:
    http.get(
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

    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

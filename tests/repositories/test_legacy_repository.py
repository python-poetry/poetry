import shutil

from pathlib import Path

import pytest
import requests

from poetry.core.packages.dependency import Dependency
from poetry.factory import Factory
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.legacy_repository import Page


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


class MockRepository(LegacyRepository):

    FIXTURES = Path(__file__).parent / "fixtures" / "legacy"

    def __init__(self):
        super(MockRepository, self).__init__(
            "legacy", url="http://legacy.foo.bar", disable_cache=True
        )

    def _get(self, endpoint):
        parts = endpoint.split("/")
        name = parts[1]

        fixture = self.FIXTURES / (name + ".html")
        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return Page(self._url + endpoint, f.read(), {})

    def _download(self, url, dest):
        filename = urlparse.urlparse(url).path.rsplit("/")[-1]
        filepath = self.FIXTURES.parent / "pypi.org" / "dists" / filename

        shutil.copyfile(str(filepath), dest)


def test_page_relative_links_path_are_correct():
    repo = MockRepository()

    page = repo._get("/relative")

    for link in page.links:
        assert link.netloc == "legacy.foo.bar"
        assert link.path.startswith("/relative/poetry")


def test_page_absolute_links_path_are_correct():
    repo = MockRepository()

    page = repo._get("/absolute")

    for link in page.links:
        assert link.netloc == "files.pythonhosted.org"
        assert link.path.startswith("/packages/")


def test_sdist_format_support():
    repo = MockRepository()
    page = repo._get("/relative")
    bz2_links = list(filter(lambda link: link.ext == ".tar.bz2", page.links))
    assert len(bz2_links) == 1
    assert bz2_links[0].filename == "poetry-0.1.1.tar.bz2"


def test_missing_version():
    repo = MockRepository()

    with pytest.raises(PackageNotFound):
        repo._get_release_info("missing_version", "1.1.0")


def test_get_package_information_fallback_read_setup():
    repo = MockRepository()

    package = repo.package("jupyter", "1.0.0")

    assert package.source_type == "legacy"
    assert package.source_reference == repo.name
    assert package.source_url == repo.url
    assert package.name == "jupyter"
    assert package.version.text == "1.0.0"
    assert (
        package.description
        == "Jupyter metapackage. Install all the Jupyter components in one go."
    )


def test_get_package_information_skips_dependencies_with_invalid_constraints():
    repo = MockRepository()

    package = repo.package("python-language-server", "0.21.2")

    assert package.name == "python-language-server"
    assert package.version.text == "0.21.2"
    assert (
        package.description == "Python Language Server for the Language Server Protocol"
    )

    assert 25 == len(package.requires)
    assert sorted(
        [r for r in package.requires if not r.is_optional()], key=lambda r: r.name
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


def test_find_packages_no_prereleases():
    repo = MockRepository()

    packages = repo.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1

    assert packages[0].source_type == "legacy"
    assert packages[0].source_reference == repo.name
    assert packages[0].source_url == repo.url


@pytest.mark.parametrize("constraint,count", [("*", 1), (">=1", 0), (">=19.0.0a0", 1)])
def test_find_packages_only_prereleases(constraint, count):
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert len(packages) == count

    if count >= 0:
        for package in packages:
            assert package.source_type == "legacy"
            assert package.source_reference == repo.name
            assert package.source_url == repo.url


def test_find_packages_only_prereleases_empty_when_not_any():
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", ">=1"))

    assert len(packages) == 0


def test_get_package_information_chooses_correct_distribution():
    repo = MockRepository()

    package = repo.package("isort", "4.3.4")

    assert package.name == "isort"
    assert package.version.text == "4.3.4"

    assert package.requires == [Dependency("futures", "*")]
    futures_dep = package.requires[0]
    assert futures_dep.python_versions == "~2.7"


def test_get_package_information_includes_python_requires():
    repo = MockRepository()

    package = repo.package("futures", "3.2.0")

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_information_sets_appropriate_python_versions_if_wheels_only():
    repo = MockRepository()

    package = repo.package("futures", "3.2.0")

    assert package.name == "futures"
    assert package.version.text == "3.2.0"
    assert package.python_versions == ">=2.6, <3"


def test_get_package_from_both_py2_and_py3_specific_wheels():
    repo = MockRepository()

    package = repo.package("ipython", "5.7.0")

    assert "ipython" == package.name
    assert "5.7.0" == package.version.text
    assert "*" == package.python_versions
    assert 41 == len(package.requires)

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
    assert expected == required

    assert 'python_version == "2.7"' == str(required[1].marker)
    assert 'sys_platform == "win32" and python_version < "3.6"' == str(
        required[12].marker
    )
    assert 'python_version == "2.7" or python_version == "3.3"' == str(
        required[4].marker
    )
    assert 'sys_platform != "win32"' == str(required[5].marker)


def test_get_package_with_dist_and_universal_py3_wheel():
    repo = MockRepository()

    package = repo.package("ipython", "7.5.0")

    assert "ipython" == package.name
    assert "7.5.0" == package.version.text
    assert ">=3.5" == package.python_versions

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
    assert expected == sorted(required, key=lambda dep: dep.name)


def test_get_package_retrieves_non_sha256_hashes():
    repo = MockRepository()

    package = repo.package("ipython", "7.5.0")

    expected = [
        {
            "file": "ipython-7.5.0-py3-none-any.whl",
            "hash": "sha256:78aea20b7991823f6a32d55f4e963a61590820e43f666ad95ad07c7f0c704efa",
        },
        {
            "file": "ipython-7.5.0.tar.gz",
            "hash": "sha256:e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26",
        },
    ]

    assert expected == package.files


def test_get_package_retrieves_non_sha256_hashes_mismatching_known_hash():
    repo = MockRepository()

    package = repo.package("ipython", "5.7.0")

    expected = [
        {
            "file": "ipython-5.7.0-py2-none-any.whl",
            "hash": "md5:a10a802ef98da741cd6f4f6289d47ba7",
        },
        {
            "file": "ipython-5.7.0-py3-none-any.whl",
            "hash": "sha256:fc0464e68f9c65cd8c453474b4175432cc29ecb6c83775baedf6dbfcee9275ab",
        },
        {
            "file": "ipython-5.7.0.tar.gz",
            "hash": "sha256:8db43a7fb7619037c98626613ff08d03dda9d5d12c84814a4504c78c0da8323c",
        },
    ]

    assert expected == package.files


def test_get_package_retrieves_packages_with_no_hashes():
    repo = MockRepository()

    package = repo.package("jupyter", "1.0.0")

    assert [
        {
            "file": "jupyter-1.0.0.tar.gz",
            "hash": "sha256:d9dc4b3318f310e34c82951ea5d6683f67bed7def4b259fafbfe4f1beb1d8e5f",
        }
    ] == package.files


class MockHttpRepository(LegacyRepository):
    def __init__(self, endpoint_responses, http):
        base_url = "http://legacy.foo.bar"
        super(MockHttpRepository, self).__init__(
            "legacy", url=base_url, disable_cache=True
        )

        for endpoint, response in endpoint_responses.items():
            url = base_url + endpoint
            http.register_uri(http.GET, url, status=response)


def test_get_200_returns_page(http):
    repo = MockHttpRepository({"/foo": 200}, http)

    assert repo._get("/foo")


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_get_40x_and_returns_none(http, status_code):
    repo = MockHttpRepository({"/foo": status_code}, http)

    assert repo._get("/foo") is None


def test_get_5xx_raises(http):
    repo = MockHttpRepository({"/foo": 500}, http)

    with pytest.raises(RepositoryError):
        repo._get("/foo")


def test_get_redirected_response_url(http, monkeypatch):
    repo = MockHttpRepository({"/foo": 200}, http)
    redirect_url = "http://legacy.redirect.bar"

    def get_mock(url):
        response = requests.Response()
        response.status_code = 200
        response.url = redirect_url + "/foo"
        return response

    monkeypatch.setattr(repo.session, "get", get_mock)
    assert repo._get("/foo")._url == "http://legacy.redirect.bar/foo/"

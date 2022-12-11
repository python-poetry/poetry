from __future__ import annotations

import re
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.core.packages.package import Package

from poetry.installation.pip_installer import PipInstaller
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.authenticator import RepositoryCertificateConfig
from poetry.utils.env import NullEnv


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.conftest import Config


@pytest.fixture
def package_git() -> Package:
    package = Package(
        "demo",
        "1.0.0",
        source_type="git",
        source_url="git@github.com:demo/demo.git",
        source_reference="master",
    )

    return package


@pytest.fixture
def package_git_with_subdirectory() -> Package:
    package = Package(
        "subdirectories",
        "2.0.0",
        source_type="git",
        source_url="https://github.com/demo/subdirectories.git",
        source_reference="master",
        source_subdirectory="two",
    )

    return package


@pytest.fixture
def pool() -> RepositoryPool:
    return RepositoryPool()


@pytest.fixture()
def env(tmp_path: Path) -> NullEnv:
    return NullEnv(path=tmp_path)


@pytest.fixture
def installer(pool: RepositoryPool, env: NullEnv) -> PipInstaller:
    return PipInstaller(env, NullIO(), pool)


def test_requirement(installer: PipInstaller):
    package = Package("ipython", "7.5.0")
    package.files = [
        {"file": "foo-0.1.0.tar.gz", "hash": "md5:dbdc53e3918f28fa335a173432402a00"},
        {
            "file": "foo.0.1.0.whl",
            "hash": "e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26",
        },
    ]

    result = installer.requirement(package, formatted=True)
    expected = (
        "ipython==7.5.0 "
        "--hash md5:dbdc53e3918f28fa335a173432402a00 "
        "--hash sha256:e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26"
        "\n"
    )

    assert result == expected


def test_requirement_source_type_url(env: NullEnv):
    installer = PipInstaller(env, NullIO(), RepositoryPool())

    foo = Package(
        "foo",
        "0.0.0",
        source_type="url",
        source_url="https://somewhere.com/releases/foo-1.0.0.tar.gz",
    )

    result = installer.requirement(foo, formatted=True)
    expected = f"{foo.source_url}#egg={foo.name}"

    assert result == expected


def test_requirement_git_subdirectory(
    pool: RepositoryPool, package_git_with_subdirectory: Package, env: NullEnv
) -> None:
    installer = PipInstaller(env, NullIO(), pool)
    result = installer.requirement(package_git_with_subdirectory)
    expected = (
        "git+https://github.com/demo/subdirectories.git"
        "@master#egg=subdirectories&subdirectory=two"
    )

    assert result == expected
    installer.install(package_git_with_subdirectory)
    assert len(env.executed) == 1
    cmd = env.executed[0]
    assert Path(cmd[-1]).parts[-3:] == ("demo", "subdirectories", "two")


def test_requirement_git_develop_false(installer: PipInstaller, package_git: Package):
    package_git.develop = False
    result = installer.requirement(package_git)
    expected = "git+git@github.com:demo/demo.git@master#egg=demo"

    assert result == expected


def test_install_with_non_pypi_default_repository(
    pool: RepositoryPool, installer: PipInstaller
):
    default = LegacyRepository("default", "https://default.com")
    another = LegacyRepository("another", "https://another.com")

    pool.add_repository(default, default=True)
    pool.add_repository(another)

    foo = Package(
        "foo",
        "0.0.0",
        source_type="legacy",
        source_reference=default.name,
        source_url=default.url,
    )
    bar = Package(
        "bar",
        "0.1.0",
        source_type="legacy",
        source_reference=another.name,
        source_url=another.url,
    )

    installer.install(foo)
    installer.install(bar)


@pytest.mark.parametrize(
    ("key", "option"),
    [
        ("client_cert", "client-cert"),
        ("cert", "cert"),
    ],
)
def test_install_with_certs(mocker: MockerFixture, key: str, option: str, env: NullEnv):
    client_path = "path/to/client.pem"
    mocker.patch(
        "poetry.utils.authenticator.Authenticator.get_certs_for_url",
        return_value=RepositoryCertificateConfig(**{key: Path(client_path)}),
    )

    default = LegacyRepository("default", "https://foo.bar")
    pool = RepositoryPool()
    pool.add_repository(default, default=True)

    installer = PipInstaller(env, NullIO(), pool)

    foo = Package(
        "foo",
        "0.0.0",
        source_type="legacy",
        source_reference=default.name,
        source_url=default.url,
    )

    installer.install(foo)

    assert len(env.executed) == 1
    cmd = env.executed[0]
    assert f"--{option}" in cmd
    cert_index = cmd.index(f"--{option}")
    # Need to do the str(Path()) bit because Windows paths get modified by Path
    assert cmd[cert_index + 1] == str(Path(client_path))


def test_requirement_git_develop_true(installer: PipInstaller, package_git: Package):
    package_git.develop = True
    result = installer.requirement(package_git)
    expected = ["-e", "git+git@github.com:demo/demo.git@master#egg=demo"]

    assert result == expected


def test_uninstall_git_package_nspkg_pth_cleanup(
    mocker: MockerFixture, tmp_venv: VirtualEnv, pool: RepositoryPool
):
    # this test scenario requires a real installation using the pip installer
    installer = PipInstaller(tmp_venv, NullIO(), pool)

    # use a namespace package
    package = Package(
        "namespace-package-one",
        "1.0.0",
        source_type="git",
        source_url="https://github.com/demo/namespace-package-one.git",
        source_reference="master",
    )

    # in order to reproduce the scenario where the git source is removed prior to proper
    # clean up of nspkg.pth file, we need to make sure the fixture is copied and not
    # symlinked into the git src directory
    def copy_only(source: Path, dest: Path) -> None:
        if dest.exists():
            dest.unlink()

        if source.is_dir():
            shutil.copytree(str(source), str(dest))
        else:
            shutil.copyfile(str(source), str(dest))

    mocker.patch("tests.helpers.copy_or_symlink", new=copy_only)

    # install package and then remove it
    installer.install(package)
    installer.remove(package)

    pth_file = f"{package.name}-nspkg.pth"
    assert not tmp_venv.site_packages.exists(pth_file)

    # any command in the virtual environment should trigger the error message
    output = tmp_venv.run("python", "-m", "site")
    assert not re.match(rf"Error processing line 1 of .*{pth_file}", output)


def test_install_with_trusted_host(config: Config, env: NullEnv):
    config.merge({"certificates": {"default": {"cert": False}}})

    default = LegacyRepository("default", "https://foo.bar")
    pool = RepositoryPool()
    pool.add_repository(default, default=True)

    installer = PipInstaller(env, NullIO(), pool)

    foo = Package(
        "foo",
        "0.0.0",
        source_type="legacy",
        source_reference=default.name,
        source_url=default.url,
    )

    installer.install(foo)

    assert len(env.executed) == 1
    cmd = env.executed[0]
    assert "--trusted-host" in cmd
    cert_index = cmd.index("--trusted-host")
    assert cmd[cert_index + 1] == "foo.bar"


def test_install_directory_fallback_on_poetry_create_error(
    mocker: MockerFixture, tmp_venv: VirtualEnv, pool: RepositoryPool
):
    mock_create_poetry = mocker.patch(
        "poetry.factory.Factory.create_poetry", side_effect=RuntimeError
    )
    mock_sdist_builder = mocker.patch("poetry.core.masonry.builders.sdist.SdistBuilder")
    mock_editable_builder = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder"
    )
    mock_pip_install = mocker.patch("poetry.installation.pip_installer.pip_install")

    package = Package(
        "demo",
        "1.0.0",
        source_type="directory",
        source_url=str(
            Path(__file__).parent.parent / "fixtures/inspection/demo_poetry_package"
        ),
    )

    installer = PipInstaller(tmp_venv, NullIO(), pool)
    installer.install_directory(package)

    assert mock_create_poetry.call_count == 1
    assert mock_sdist_builder.call_count == 0
    assert mock_editable_builder.call_count == 0
    assert mock_pip_install.call_count == 1
    assert mock_pip_install.call_args[1].get("deps") is None
    assert mock_pip_install.call_args[1].get("upgrade") is True

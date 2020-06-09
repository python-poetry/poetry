import shutil

import pytest

from poetry.core.packages.package import Package
from poetry.installation.pip_installer import PipInstaller
from poetry.io.null_io import NullIO
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pool import Pool
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv


@pytest.fixture
def package_git():
    package = Package("demo", "1.0.0")
    package.source_type = "git"
    package.source_url = "git@github.com:demo/demo.git"
    package.source_reference = "master"
    return package


@pytest.fixture
def pool():
    return Pool()


@pytest.fixture
def installer(pool):
    return PipInstaller(NullEnv(), NullIO(), pool)


def test_requirement(installer):
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

    assert expected == result


def test_requirement_source_type_url():
    installer = PipInstaller(NullEnv(), NullIO(), Pool())

    foo = Package("foo", "0.0.0")
    foo.source_type = "url"
    foo.source_url = "https://somehwere.com/releases/foo-1.0.0.tar.gz"

    result = installer.requirement(foo, formatted=True)
    expected = "{}#egg={}".format(foo.source_url, foo.name)

    assert expected == result


def test_requirement_git_develop_false(installer, package_git):
    package_git.develop = False
    result = installer.requirement(package_git)
    expected = "git+git@github.com:demo/demo.git@master#egg=demo"

    assert expected == result


def test_install_with_non_pypi_default_repository(pool, installer):
    default = LegacyRepository("default", "https://default.com")
    another = LegacyRepository("another", "https://another.com")

    pool.add_repository(default, default=True)
    pool.add_repository(another)

    foo = Package("foo", "0.0.0")
    foo.source_type = "legacy"
    foo.source_reference = default._name
    foo.source_url = default._url
    bar = Package("bar", "0.1.0")
    bar.source_type = "legacy"
    bar.source_reference = another._name
    bar.source_url = another._url

    installer.install(foo)
    installer.install(bar)


def test_install_with_cert():
    ca_path = "path/to/cert.pem"
    pool = Pool()

    default = LegacyRepository("default", "https://foo.bar", cert=Path(ca_path))

    pool.add_repository(default, default=True)

    null_env = NullEnv()

    installer = PipInstaller(null_env, NullIO(), pool)

    foo = Package("foo", "0.0.0")
    foo.source_type = "legacy"
    foo.source_reference = default._name
    foo.source_url = default._url

    installer.install(foo)

    assert len(null_env.executed) == 1
    cmd = null_env.executed[0]
    assert "--cert" in cmd
    cert_index = cmd.index("--cert")
    # Need to do the str(Path()) bit because Windows paths get modified by Path
    assert cmd[cert_index + 1] == str(Path(ca_path))


def test_install_with_client_cert():
    client_path = "path/to/client.pem"
    pool = Pool()

    default = LegacyRepository(
        "default", "https://foo.bar", client_cert=Path(client_path)
    )

    pool.add_repository(default, default=True)

    null_env = NullEnv()

    installer = PipInstaller(null_env, NullIO(), pool)

    foo = Package("foo", "0.0.0")
    foo.source_type = "legacy"
    foo.source_reference = default._name
    foo.source_url = default._url

    installer.install(foo)

    assert len(null_env.executed) == 1
    cmd = null_env.executed[0]
    assert "--client-cert" in cmd
    cert_index = cmd.index("--client-cert")
    # Need to do the str(Path()) bit because Windows paths get modified by Path
    assert cmd[cert_index + 1] == str(Path(client_path))


def test_requirement_git_develop_true(installer, package_git):
    package_git.develop = True
    result = installer.requirement(package_git)
    expected = ["-e", "git+git@github.com:demo/demo.git@master#egg=demo"]

    assert expected == result


def test_uninstall_git_package_nspkg_pth_cleanup(mocker, tmp_venv, pool):
    # this test scenario requires a real installation using the pip installer
    installer = PipInstaller(tmp_venv, NullIO(), pool)

    # use a namepspace package
    package = Package("namespace-package-one", "1.0.0")
    package.source_type = "git"
    package.source_url = "https://github.com/demo/namespace-package-one.git"
    package.source_reference = "master"
    package.develop = True

    # we do this here because the virtual env might not be usable if failure case is triggered
    pth_file_candidate = tmp_venv.site_packages / "{}-nspkg.pth".format(package.name)

    # in order to reproduce the scenario where the git source is removed prior to proper
    # clean up of nspkg.pth file, we need to make sure the fixture is copied and not
    # symlinked into the git src directory
    def copy_only(source, dest):
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

    assert not Path(pth_file_candidate).exists()

    # any command in the virtual environment should trigger the error message
    output = tmp_venv.run("python", "-m", "site")
    assert "Error processing line 1 of {}".format(pth_file_candidate) not in output

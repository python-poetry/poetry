from tests.helpers import get_package
from poetry.installation.pip_installer import PipInstaller
from poetry.io import NullIO
from poetry.packages.package import Package
from poetry.utils.env import NullEnv


def test_requirement():
    installer = PipInstaller(NullEnv(), NullIO())

    package = Package("ipython", "7.5.0")
    package.hashes = [
        "md5:dbdc53e3918f28fa335a173432402a00",
        "e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26",
    ]

    result = installer.requirement(package, formatted=True)
    expected = (
        "ipython==7.5.0 "
        "--hash md5:dbdc53e3918f28fa335a173432402a00 "
        "--hash sha256:e840810029224b56cd0d9e7719dc3b39cf84d577f8ac686547c8ba7a06eeab26"
        "\n"
    )

    assert expected == result


def test_pip_install_legacy_password(mocker, config):
    config.add_property("http-basic.foo.username", "foo")
    config.add_property("http-basic.foo.password", "bar/?#@:")
    mocker.patch("poetry.installation.pip_installer.Config.create", return_value=config)

    installer = PipInstaller(NullEnv(), NullIO())
    run = mocker.patch.object(installer, "run")

    package = get_package("A", "1.0")
    package.source_type = "legacy"
    package.source_reference = "foo"
    package.source_url = "https://www.example.com/pypi/simple"

    installer.install(package)

    assert run.call_args == mocker.call(
        "install",
        "--no-deps",
        "--index-url",
        "https://foo:bar%2F%3F%23%40%3A@www.example.com/pypi/simple",
        "a==1.0",
    )

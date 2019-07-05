from poetry.installation.pip_installer import PipInstaller
from poetry.io.null_io import NullIO
from poetry.packages.package import Package
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import NullEnv


def test_requirement():
    installer = PipInstaller(NullEnv(), NullIO(), Pool())

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


def test_install_with_non_pypi_default_repository():
    pool = Pool()

    default = LegacyRepository("default", "https://default.com")
    another = LegacyRepository("another", "https://another.com")

    pool.add_repository(default, default=True)
    pool.add_repository(another)

    installer = PipInstaller(NullEnv(), NullIO(), pool)

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

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

from poetry.packages import Dependency
from poetry.packages import Package


def test_accepts():
    dependency = Dependency('A', '^1.0')
    package = Package('A', '1.4')

    assert dependency.accepts(package)


def test_accepts_prerelease():
    dependency = Dependency('A', '^1.0', allows_prereleases=True)
    package = Package('A', '1.4-beta.1')

    assert dependency.accepts(package)


def test_accepts_python_versions():
    dependency = Dependency('A', '^1.0')
    dependency.python_versions = '^3.6'
    package = Package('A', '1.4')
    package.python_versions = '~3.6'

    assert dependency.accepts(package)


def test_accepts_fails_with_different_names():
    dependency = Dependency('A', '^1.0')
    package = Package('B', '1.4')

    assert not dependency.accepts(package)


def test_accepts_fails_with_version_mismatch():
    dependency = Dependency('A', '~1.0')
    package = Package('B', '1.4')

    assert not dependency.accepts(package)


def test_accepts_fails_with_prerelease_mismatch():
    dependency = Dependency('A', '^1.0')
    package = Package('B', '1.4-beta.1')

    assert not dependency.accepts(package)


def test_accepts_fails_with_python_versions_mismatch():
    dependency = Dependency('A', '^1.0')
    dependency.python_versions = '^3.6'
    package = Package('B', '1.4')
    package.python_versions = '~3.5'

    assert not dependency.accepts(package)

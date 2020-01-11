import pytest

from poetry.bundle.bundler import Bundler
from poetry.bundle.bundler_manager import BundlerManager
from poetry.bundle.exceptions import BundlerManagerError


class MockBundler(Bundler):
    @property
    def name(self):  # type: () -> str
        return "mock"


def test_manager_has_default_bundlers():
    manager = BundlerManager()

    assert len(manager.bundlers) > 0


def test_bundler_returns_the_correct_bundler():
    manager = BundlerManager()

    bundler = manager.bundler("venv")
    assert isinstance(bundler, Bundler)
    assert "venv" == bundler.name


def test_bundler_raises_an_error_for_incorrect_bundlers():
    manager = BundlerManager()

    with pytest.raises(BundlerManagerError, match='The bundler "mock" does not exist.'):
        manager.bundler("mock")


def test_register_bundler_registers_new_bundlers():
    manager = BundlerManager()
    manager.register_bundler(MockBundler())

    bundler = manager.bundler("mock")
    assert isinstance(bundler, Bundler)
    assert "mock" == bundler.name


def test_register_bundler_cannot_register_existing_bundlers():
    manager = BundlerManager()
    manager.register_bundler(MockBundler())

    with pytest.raises(
        BundlerManagerError, match='A bundler with the name "mock" already exists.'
    ):
        manager.register_bundler(MockBundler())

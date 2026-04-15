from __future__ import annotations

import os

from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

import keyring
import pytest

from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link

from poetry.repositories.exceptions import PackageNotFoundError
from poetry.utils.password_manager import PoetryKeyring
from tests.helpers import FIXTURE_PATH
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import MockDulwichRepo
from tests.helpers import TestLocker
from tests.helpers import TestRepository
from tests.helpers import copy_path
from tests.helpers import flatten_dict
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.helpers import isolated_environment
from tests.helpers import make_entry_point_from_plugin
from tests.helpers import mock_clone
from tests.helpers import mock_metadata_entry_points
from tests.helpers import pbs_installer_supported_arch
from tests.helpers import switch_working_directory
from tests.helpers import with_working_directory


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- get_package ---


class TestGetPackage:
    def test_returns_package_with_name_and_version(self) -> None:
        package = get_package("foo", "1.0.0")
        assert isinstance(package, Package)
        assert package.name == "foo"
        assert package.version.text == "1.0.0"

    def test_returns_package_not_yanked_by_default(self) -> None:
        package = get_package("foo", "1.0.0")
        assert package.yanked is False

    def test_returns_yanked_package_with_string_reason(self) -> None:
        package = get_package("foo", "1.0.0", yanked="security issue")
        assert package.yanked is True

    def test_returns_yanked_package_with_bool(self) -> None:
        package = get_package("foo", "1.0.0", yanked=True)
        assert package.yanked is True


# --- get_dependency ---


class TestGetDependency:
    def test_returns_dependency_with_wildcard_constraint(self) -> None:
        dep = get_dependency("foo")
        assert dep.name == "foo"
        assert str(dep.constraint) == "*"

    def test_returns_dependency_with_version_constraint(self) -> None:
        dep = get_dependency("foo", ">=1.0")
        assert dep.name == "foo"

    def test_returns_dependency_with_dict_constraint(self) -> None:
        dep = get_dependency("foo", {"version": ">=1.0", "python": "^3.10"})
        assert dep.name == "foo"

    def test_returns_optional_dependency(self) -> None:
        dep = get_dependency("foo", ">=1.0", optional=True)
        assert dep.is_optional()

    def test_returns_dependency_with_groups(self) -> None:
        dep = get_dependency("foo", ">=1.0", groups=["dev"])
        assert dep.in_extras == []

    def test_returns_dependency_allowing_prereleases(self) -> None:
        dep = get_dependency("foo", ">=1.0", allows_prereleases=True)
        assert dep.allows_prereleases()


# --- copy_path ---


class TestCopyPath:
    def test_copies_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("hello")
        dest = tmp_path / "dest.txt"

        copy_path(source, dest)

        assert dest.read_text() == "hello"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")

        copy_path(source, dest)

        assert dest.read_text() == "new content"

    def test_copies_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("content")
        dest = tmp_path / "dest_dir"

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "file.txt").read_text() == "content"

    def test_overwrites_existing_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "new_file.txt").write_text("new")

        dest = tmp_path / "dest_dir"
        dest.mkdir()
        (dest / "old_file.txt").write_text("old")

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "new_file.txt").read_text() == "new"
        assert not (dest / "old_file.txt").exists()


# --- MockDulwichRepo ---


class TestMockDulwichRepo:
    def test_stores_path_as_string(self) -> None:
        repo = MockDulwichRepo(Path("/some/path"))
        assert repo.path == "/some/path"

    def test_stores_string_path(self) -> None:
        repo = MockDulwichRepo("/some/path")
        assert repo.path == "/some/path"

    def test_head_returns_mock_revision(self) -> None:
        repo = MockDulwichRepo("/some/path")
        assert repo.head() == MOCK_DEFAULT_GIT_REVISION.encode()

    def test_ignores_extra_kwargs(self) -> None:
        repo = MockDulwichRepo(Path("/some/path"), extra="ignored")
        assert repo.path == "/some/path"


# --- mock_clone ---


class TestMockClone:
    def test_clones_fixture_to_source_root(self, tmp_path: Path) -> None:
        url = "https://github.com/demo/demo.git"
        result = mock_clone(url, source_root=tmp_path)

        assert isinstance(result, MockDulwichRepo)
        dest = tmp_path / "demo"
        assert dest.is_dir()
        assert result.path == str(dest)

    def test_clones_fixture_with_nested_path(self, tmp_path: Path) -> None:
        url = "https://github.com/demo/subdirectories.git"
        result = mock_clone(url, source_root=tmp_path)

        assert isinstance(result, MockDulwichRepo)
        dest = tmp_path / "subdirectories"
        assert dest.is_dir()


# --- TestLocker ---


class TestTestLocker:
    def test_is_not_locked_by_default(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        assert locker.is_locked() is False

    def test_locked_sets_locked_state(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        result = locker.locked()
        assert locker.is_locked() is True
        assert result is locker

    def test_locked_with_false(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        locker.locked()
        locker.locked(False)
        assert locker.is_locked() is False

    def test_is_fresh_always_returns_true(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        assert locker.is_fresh() is True

    def test_mock_lock_data_sets_data(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        data = {"package": [], "metadata": {}}
        locker.mock_lock_data(data)
        assert locker.is_locked() is True
        assert locker.lock_data == data

    def test_write_lock_data_without_write_stores_in_memory(
        self, tmp_path: Path
    ) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})

        from tomlkit import document

        data = document()
        data["metadata"] = {"lock-version": "2.1"}
        locker._write_lock_data(data)

        assert locker._lock_data == data
        assert not lock_path.exists()

    def test_write_lock_data_with_write_persists_to_file(
        self, tmp_path: Path
    ) -> None:
        lock_path = tmp_path / "poetry.lock"
        locker = TestLocker(lock_path, {})
        locker.write()

        from tomlkit import document

        data = document()
        data["metadata"] = {"lock-version": "2.1"}
        locker._write_lock_data(data)

        assert lock_path.exists()
        assert locker.is_locked() is True


# --- TestRepository ---


class TestTestRepository:
    def test_find_packages_returns_matching_packages(self) -> None:
        repo = TestRepository("test")
        package = get_package("foo", "1.0.0")
        repo.add_package(package)

        dep = get_dependency("foo", ">=1.0")
        result = repo.find_packages(dep)
        assert len(result) == 1
        assert result[0].name == "foo"

    def test_find_packages_raises_when_not_found(self) -> None:
        repo = TestRepository("test")

        dep = get_dependency("nonexistent", ">=1.0")
        with pytest.raises(PackageNotFoundError, match="nonexistent"):
            repo.find_packages(dep)

    def test_find_links_for_package_returns_wheel_link(self) -> None:
        repo = TestRepository("test")
        package = get_package("my-package", "1.2.3")

        links = repo.find_links_for_package(package)
        assert len(links) == 1
        assert isinstance(links[0], Link)
        assert "my_package-1.2.3-py2.py3-none-any.whl" in str(links[0])


# --- isolated_environment ---


class TestIsolatedEnvironment:
    def test_restores_original_environ(self) -> None:
        original_environ = dict(os.environ)
        with isolated_environment():
            os.environ["TEST_VAR"] = "test"
        assert os.environ == original_environ

    def test_clears_environ(self) -> None:
        os.environ["TEST_VAR"] = "test"
        with isolated_environment(clear=True):
            assert "TEST_VAR" not in os.environ
        assert "TEST_VAR" in os.environ

    def test_updates_environ(self) -> None:
        with isolated_environment(environ={"NEW_VAR": "new_value"}):
            assert os.environ["NEW_VAR"] == "new_value"
        assert "NEW_VAR" not in os.environ

    def test_clears_and_updates_environ(self) -> None:
        os.environ["EXISTING_VAR"] = "existing"
        with isolated_environment(
            environ={"INJECTED_VAR": "injected"}, clear=True
        ):
            assert "EXISTING_VAR" not in os.environ
            assert os.environ["INJECTED_VAR"] == "injected"
        assert os.environ.get("EXISTING_VAR") == "existing"
        assert "INJECTED_VAR" not in os.environ


# --- make_entry_point_from_plugin ---


class TestMakeEntryPointFromPlugin:
    def test_creates_entry_point_without_dist(self) -> None:
        class FakePlugin:
            group = "poetry.plugin"
            __module__ = "my_plugin.plugin"

        ep = make_entry_point_from_plugin("test-plugin", FakePlugin)
        assert isinstance(ep, metadata.EntryPoint)
        assert ep.name == "test-plugin"
        assert ep.group == "poetry.plugin"
        assert ep.value == "my_plugin.plugin:FakePlugin"

    def test_creates_entry_point_without_group_attr(self) -> None:
        class NoGroupPlugin:
            __module__ = "my_plugin.plugin"
            __name__ = "NoGroupPlugin"

        ep = make_entry_point_from_plugin("test-plugin", NoGroupPlugin)
        assert ep.group is None


# --- mock_metadata_entry_points ---


class TestMockMetadataEntryPoints:
    def test_patches_entry_points(self, mocker: MockerFixture) -> None:
        class FakePlugin:
            group = "poetry.plugin"
            __module__ = "my_plugin"
            __name__ = "FakePlugin"

        mock_metadata_entry_points(mocker, FakePlugin, name="my-plugin")

        eps = metadata.entry_points(group="poetry.plugin")
        assert len(eps) == 1
        assert eps[0].name == "my-plugin"

    def test_returns_empty_for_different_group(
        self, mocker: MockerFixture
    ) -> None:
        class FakePlugin:
            group = "poetry.plugin"
            __module__ = "my_plugin"
            __name__ = "FakePlugin"

        mock_metadata_entry_points(mocker, FakePlugin)

        eps = metadata.entry_points(group="some.other.group")
        assert eps == []


# --- flatten_dict ---


class TestFlattenDict:
    def test_flattens_nested_dict(self) -> None:
        orig_dict = {
            "a": 1,
            "b": 2,
            "c": {
                "x": 8,
                "y": 9,
            },
        }

        flattened_dict = {
            "a": 1,
            "b": 2,
            "c:x": 8,
            "c:y": 9,
        }

        assert flattened_dict == flatten_dict(orig_dict, delimiter=":")

    def test_flattens_with_default_delimiter(self) -> None:
        orig_dict = {"a": {"b": 1}}
        assert flatten_dict(orig_dict) == {"a.b": 1}

    def test_flattens_deeply_nested_dict(self) -> None:
        orig_dict = {"a": {"b": {"c": {"d": 42}}}}
        assert flatten_dict(orig_dict) == {"a.b.c.d": 42}

    def test_returns_flat_dict_unchanged(self) -> None:
        orig_dict = {"a": 1, "b": 2}
        assert flatten_dict(orig_dict) == {"a": 1, "b": 2}

    def test_handles_empty_dict(self) -> None:
        assert flatten_dict({}) == {}


# --- switch_working_directory ---


class TestSwitchWorkingDirectory:
    @pytest.mark.parametrize("remove", [False, True])
    @pytest.mark.parametrize("raise_error", [False, True])
    def test_changes_restores_and_removes(
        self, tmp_path: Path, remove: bool, raise_error: bool
    ) -> None:
        original_cwd = os.getcwd()
        temp_dir = tmp_path / f"temp-working-dir-{remove}-{raise_error}"
        temp_dir.mkdir()

        if raise_error:
            with (
                pytest.raises(RuntimeError),
                switch_working_directory(temp_dir, remove=remove),
            ):
                assert os.getcwd() == str(temp_dir)
                raise RuntimeError("boom")
        else:
            with switch_working_directory(temp_dir, remove=remove):
                assert os.getcwd() == str(temp_dir)

        assert os.getcwd() == original_cwd
        assert temp_dir.exists() is (not remove)


# --- with_working_directory ---


class TestWithWorkingDirectory:
    def test_without_copy(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("content")

        original_cwd = os.getcwd()
        with with_working_directory(source) as path:
            assert os.getcwd() == str(source)
            assert path == source
            assert (path / "file.txt").read_text() == "content"

        assert os.getcwd() == original_cwd
        assert source.exists()

    def test_with_copy(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("content")

        target = tmp_path / "target_dir"
        original_cwd = os.getcwd()

        with with_working_directory(source, target=target) as path:
            assert os.getcwd() == str(target)
            assert path == target
            assert (path / "file.txt").read_text() == "content"

        assert os.getcwd() == original_cwd
        # target should be removed after context manager exits
        assert not target.exists()
        # source should remain untouched
        assert source.exists()


# --- set_keyring_backend ---


class TestSetKeyringBackend:
    def test_sets_keyring_backend_and_clears_cache(self) -> None:
        from keyring.backend import KeyringBackend

        class DummyBackend(KeyringBackend):
            priority = 1  # type: ignore[assignment]

            def get_password(
                self, service: str, username: str
            ) -> str | None:
                return None

            def set_password(
                self, service: str, username: str, password: str
            ) -> None:
                pass

            def delete_password(self, service: str, username: str) -> None:
                pass

        backend = DummyBackend()

        # Populate the cache before calling set_keyring_backend
        PoetryKeyring.is_available()

        from tests.helpers import set_keyring_backend

        set_keyring_backend(backend)
        assert keyring.get_keyring() is backend


# --- pbs_installer_supported_arch ---


class TestPbsInstallerSupportedArch:
    @pytest.mark.parametrize(
        "arch",
        ["arm64", "aarch64", "amd64", "x86_64", "i686", "x86"],
    )
    def test_supported_architectures(self, arch: str) -> None:
        assert pbs_installer_supported_arch(arch) is True

    @pytest.mark.parametrize(
        "arch",
        ["ARM64", "AARCH64", "AMD64", "X86_64"],
    )
    def test_case_insensitive(self, arch: str) -> None:
        assert pbs_installer_supported_arch(arch) is True

    @pytest.mark.parametrize(
        "arch",
        ["mips", "riscv64", "sparc", "ppc64le", "s390x", ""],
    )
    def test_unsupported_architectures(self, arch: str) -> None:
        assert pbs_installer_supported_arch(arch) is False

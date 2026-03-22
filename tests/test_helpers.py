from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from tests.helpers import copy_path
from tests.helpers import flatten_dict
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.helpers import isolated_environment
from tests.helpers import pbs_installer_supported_arch
from tests.helpers import switch_working_directory
from tests.helpers import with_working_directory


if TYPE_CHECKING:
    from pathlib import Path


class TestGetPackage:
    def test_creates_package_with_name_and_version(self) -> None:
        package = get_package("foo", "1.0.0")
        assert package.name == "foo"
        assert str(package.version) == "1.0.0"
        assert package.yanked is False

    def test_creates_package_with_yanked_bool(self) -> None:
        package = get_package("foo", "1.0.0", yanked=True)
        assert package.yanked is True

    def test_creates_package_with_yanked_string(self) -> None:
        # When yanked is a non-empty string, it's treated as truthy
        package = get_package("foo", "1.0.0", yanked="security issue")
        assert package.yanked is True


class TestGetDependency:
    def test_creates_dependency_with_name_only(self) -> None:
        dep = get_dependency("foo")
        assert dep.name == "foo"
        assert str(dep.constraint) == "*"
        assert dep.is_optional() is False

    def test_creates_dependency_with_version_constraint(self) -> None:
        dep = get_dependency("foo", "^1.0")
        assert dep.name == "foo"
        assert "1.0" in str(dep.constraint)

    def test_creates_dependency_with_dict_constraint(self) -> None:
        dep = get_dependency("foo", {"version": "^1.0", "extras": ["bar"]})
        assert dep.name == "foo"
        assert "1.0" in str(dep.constraint)

    def test_creates_optional_dependency(self) -> None:
        dep = get_dependency("foo", optional=True)
        assert dep.is_optional() is True

    def test_creates_dependency_with_groups(self) -> None:
        dep = get_dependency("foo", groups=["dev"])
        assert "dev" in dep.groups

    def test_creates_dependency_with_prereleases(self) -> None:
        dep = get_dependency("foo", allows_prereleases=True)
        assert dep.allows_prereleases() is True


class TestCopyPath:
    def test_copies_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("hello")
        dest = tmp_path / "dest.txt"

        copy_path(source, dest)

        assert dest.read_text() == "hello"

    def test_copies_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("hello")
        dest = tmp_path / "dest_dir"

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "file.txt").read_text() == "hello"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")

        copy_path(source, dest)

        assert dest.read_text() == "new content"

    def test_overwrites_existing_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "new.txt").write_text("new")

        dest = tmp_path / "dest_dir"
        dest.mkdir()
        (dest / "old.txt").write_text("old")

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "new.txt").read_text() == "new"
        assert not (dest / "old.txt").exists()


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

    def test_deeply_nested_dict(self) -> None:
        orig_dict = {
            "a": {
                "b": {
                    "c": 1,
                },
            },
        }

        assert flatten_dict(orig_dict) == {"a.b.c": 1}

    def test_empty_dict(self) -> None:
        assert flatten_dict({}) == {}

    def test_flat_dict(self) -> None:
        orig_dict = {"a": 1, "b": 2}
        assert flatten_dict(orig_dict) == orig_dict


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


class TestWithWorkingDirectory:
    def test_changes_to_source_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("hello")
        original_cwd = os.getcwd()

        with with_working_directory(source) as path:
            assert os.getcwd() == str(source)
            assert path == source
            assert (path / "test.txt").read_text() == "hello"

        assert os.getcwd() == original_cwd

    def test_copies_to_target_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("hello")
        target = tmp_path / "target"
        original_cwd = os.getcwd()

        with with_working_directory(source, target) as path:
            assert os.getcwd() == str(target)
            assert path == target
            assert (path / "test.txt").read_text() == "hello"

        # Target should be cleaned up when using a copy
        assert os.getcwd() == original_cwd
        assert not target.exists()

    def test_modifies_copied_files_not_source(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("original")
        target = tmp_path / "target"

        with with_working_directory(source, target):
            (target / "test.txt").write_text("modified")

        # Source should be unchanged
        assert (source / "test.txt").read_text() == "original"


class TestPbsInstallerSupportedArch:
    @pytest.mark.parametrize(
        "arch,expected",
        [
            ("arm64", True),
            ("ARM64", True),
            ("aarch64", True),
            ("AARCH64", True),
            ("amd64", True),
            ("AMD64", True),
            ("x86_64", True),
            ("X86_64", True),
            ("i686", True),
            ("I686", True),
            ("x86", True),
            ("X86", True),
            ("ppc64", False),
            ("mips", False),
            ("unknown", False),
            ("", False),
        ],
    )
    def test_supported_architectures(self, arch: str, expected: bool) -> None:
        assert pbs_installer_supported_arch(arch) is expected

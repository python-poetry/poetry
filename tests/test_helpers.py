from __future__ import annotations

import os
import shutil

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from tests.helpers import copy_path
from tests.helpers import flatten_dict
from tests.helpers import get_package
from tests.helpers import get_dependency
from tests.helpers import isolated_environment
from tests.helpers import switch_working_directory
from tests.helpers import with_working_directory
from tests.helpers import pbs_installer_supported_arch
from tests.helpers import make_entry_point_from_plugin
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import MockDulwichRepo


if TYPE_CHECKING:
    from pathlib import Path


def test_flatten_dict() -> None:
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


def test_flatten_dict_default_delimiter() -> None:
    orig_dict = {"a": {"b": 1}, "c": 2}
    flattened = flatten_dict(orig_dict)
    assert flattened == {"a.b": 1, "c": 2}


def test_flatten_dict_empty_dict() -> None:
    assert flatten_dict({}) == {}


def test_flatten_dict_nested_empty() -> None:
    orig_dict = {"a": {}, "b": 1}
    flattened = flatten_dict(orig_dict)
    assert flattened == {"a": {}, "b": 1}


def test_isolated_environment_restores_original_environ() -> None:
    original_environ = dict(os.environ)
    with isolated_environment():
        os.environ["TEST_VAR"] = "test"
    assert os.environ == original_environ


def test_isolated_environment_clears_environ() -> None:
    os.environ["TEST_VAR"] = "test"
    with isolated_environment(clear=True):
        assert "TEST_VAR" not in os.environ
    assert "TEST_VAR" in os.environ


def test_isolated_environment_updates_environ() -> None:
    with isolated_environment(environ={"NEW_VAR": "new_value"}):
        assert os.environ["NEW_VAR"] == "new_value"
    assert "NEW_VAR" not in os.environ


@pytest.mark.parametrize("remove", [False, True])
@pytest.mark.parametrize("raise_error", [False, True])
def test_switch_working_directory_changes_restores_and_removes(
    tmp_path: Path, remove: bool, raise_error: bool
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


def test_copy_path_file_to_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("hello")
    dest = tmp_path / "dest.txt"

    copy_path(source, dest)

    assert dest.exists()
    assert dest.read_text() == "hello"


def test_copy_path_file_overwrites_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("new content")
    dest = tmp_path / "dest.txt"
    dest.write_text("old content")

    copy_path(source, dest)

    assert dest.read_text() == "new content"


def test_copy_path_dir_to_dir(tmp_path: Path) -> None:
    source = tmp_path / "source_dir"
    source.mkdir()
    (source / "file.txt").write_text("content")

    dest = tmp_path / "dest_dir"

    copy_path(source, dest)

    assert dest.is_dir()
    assert (dest / "file.txt").read_text() == "content"


def test_copy_path_dir_overwrites_existing_dir(tmp_path: Path) -> None:
    source = tmp_path / "source_dir"
    source.mkdir()
    (source / "new_file.txt").write_text("new content")

    dest = tmp_path / "dest_dir"
    dest.mkdir()
    (dest / "old_file.txt").write_text("old content")

    copy_path(source, dest)

    assert dest.is_dir()
    assert (dest / "new_file.txt").read_text() == "new content"
    assert not (dest / "old_file.txt").exists()


def test_get_package_basic() -> None:
    pkg = get_package("requests", "2.28.0")
    assert pkg.name == "requests"
    assert str(pkg.version) == "2.28.0"


def test_get_package_yanked_string() -> None:
    pkg = get_package("package", "1.0.0", yanked="yanked by author")
    assert pkg.yanked == "yanked by author"


def test_get_package_yanked_bool() -> None:
    pkg = get_package("package", "1.0.0", yanked=True)
    assert pkg.yanked is True


def test_get_dependency_basic() -> None:
    dep = get_dependency("requests")
    assert dep.name == "requests"


def test_get_dependency_with_constraint_string() -> None:
    dep = get_dependency("requests", constraint=">=2.0.0")
    assert dep.name == "requests"


def test_get_dependency_with_constraint_dict() -> None:
    dep = get_dependency("requests", constraint={"version": ">=2.0.0", "python": "^3.7"})
    assert dep.name == "requests"


def test_get_dependency_optional() -> None:
    dep = get_dependency("requests", optional=True)
    assert dep.is_optional()


def test_get_dependency_prereleases() -> None:
    dep = get_dependency("requests", allows_prereleases=True)
    assert dep.allows_prereleases


def test_get_dependency_with_groups() -> None:
    dep = get_dependency("requests", groups=["dev", "test"])
    assert "dev" in dep.groups
    assert "test" in dep.groups


@pytest.mark.parametrize(
    "arch,expected",
    [
        ("arm64", True),
        ("aarch64", True),
        ("amd64", True),
        ("x86_64", True),
        ("i686", True),
        ("x86", True),
        ("ARM64", True),
        ("AARCH64", True),
        ("ppc64", False),
        ("s390x", False),
        ("unknown", False),
        ("", False),
    ],
)
def test_pbs_installer_supported_arch(arch: str, expected: bool) -> None:
    assert pbs_installer_supported_arch(arch) is expected


def test_mock_dulwich_repo_head() -> None:
    repo = MockDulwichRepo("/some/path")
    assert repo.head() == MOCK_DEFAULT_GIT_REVISION.encode()


def test_mock_dulwich_repo_path() -> None:
    repo = MockDulwichRepo("/some/path")
    assert repo.path == "/some/path"


class DummyPlugin:
    """A dummy plugin class for testing entry points."""

    group = "poetry.plugins"


def test_make_entry_point_from_plugin() -> None:
    ep = make_entry_point_from_plugin("my-plugin", DummyPlugin)

    assert ep.name == "my-plugin"
    assert ep.group == "poetry.plugins"
    assert "DummyPlugin" in ep.value


def test_make_entry_point_with_dist() -> None:
    dist = MagicMock()
    dist.name = "my-package"
    dist.metadata = MagicMock()
    dist.metadata.json = MagicMock(return_value={})

    ep = make_entry_point_from_plugin("another-plugin", DummyPlugin, dist=dist)

    assert ep.name == "another-plugin"


def test_with_working_directory_copies_and_restores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_cwd = tmp_path.parent / "original_cwd"
    original_cwd.mkdir(exist_ok=True)
    monkeypatch.chdir(original_cwd)

    source = tmp_path / "source_dir"
    source.mkdir()
    (source / "file.txt").write_text("test content")

    target = tmp_path / "target_dir"

    with with_working_directory(source, target) as path:
        assert path == target
        assert os.getcwd() == str(target)
        assert (target / "file.txt").read_text() == "test content"

    assert os.getcwd() == str(original_cwd)


def test_with_working_directory_without_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_cwd = tmp_path.parent / "original_cwd"
    original_cwd.mkdir(exist_ok=True)
    monkeypatch.chdir(original_cwd)

    source = tmp_path / "source_dir"
    source.mkdir()

    with with_working_directory(source) as path:
        assert path == source
        assert os.getcwd() == str(source)

    assert os.getcwd() == str(original_cwd)

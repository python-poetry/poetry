from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version

from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import MockDulwichRepo
from tests.helpers import copy_path
from tests.helpers import flatten_dict
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.helpers import isolated_environment


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package


class TestGetPackage:
    @pytest.fixture
    def base_package(self) -> Package:
        return get_package("test-package", "1.0.0")

    def test_get_package_with_string_name(self, base_package: Package) -> None:
        assert base_package.name == "test-package"

    @pytest.mark.parametrize(
        "version_input,expected_version",
        [("1.0.0", "1.0.0"), (Version.parse("2.0.0"), "2.0.0")],
    )
    def test_get_package_version_handling(
        self, version_input: str | Version, expected_version: str
    ) -> None:
        package = get_package("test-package", version_input)
        assert str(package.version) == expected_version

    @pytest.mark.parametrize(
        "yanked_input,expected_yanked,expected_reason",
        [
            (False, False, None),
            (True, True, None),
            ("security vulnerability", True, "security vulnerability"),
        ],
    )
    def test_get_package_yanked_handling(
        self,
        yanked_input: bool | str,
        expected_yanked: bool,
        expected_reason: str | None,
    ) -> None:
        package = get_package("test-package", "1.0.0", yanked=yanked_input)
        assert package.yanked is expected_yanked
        if isinstance(yanked_input, str):
            assert package.yanked_reason == expected_reason


class TestGetDependency:
    @pytest.fixture
    def base_dependency(self) -> Dependency:
        return get_dependency("test-package")

    def test_get_dependency_name(self, base_dependency: Dependency) -> None:
        assert base_dependency.name == "test-package"

    def test_get_dependency_default_constraint_value(
        self, base_dependency: Dependency
    ) -> None:
        assert str(base_dependency.constraint) == "*"

    def test_get_dependency_defaults_to_false_optional(
        self, base_dependency: Dependency
    ) -> None:
        assert base_dependency.is_optional() is False

    def test_get_dependency_default_to_false_allow_prereleases(
        self, base_dependency: Dependency
    ) -> None:
        assert base_dependency.allows_prereleases() is False

    @pytest.mark.parametrize(
        "constraint,expected_constraint",
        [(None, "*"), ("^1.0.0", "^1.0.0"), ({"version": "^2.0.0"}, "^2.0.0")],
    )
    def test_get_dependency_constraint_handling(
        self, constraint: None | str | dict[str, str], expected_constraint: str
    ) -> None:
        dependency = get_dependency("test-package", constraint)
        assert dependency.pretty_constraint == expected_constraint

    def test_get_dependency_with_complex_dict_constraint(self) -> None:
        constraint = {"version": "^2.0.0", "extras": ["feature1"]}
        dependency = get_dependency("test-package", constraint)
        assert dependency.pretty_constraint == "^2.0.0"
        assert "feature1" in dependency.extras

    def test_get_dependency_with_groups(self) -> None:
        dependency = get_dependency("test-package", groups=["dev", "test"])
        assert dependency.groups == frozenset(["dev", "test"])

    @pytest.mark.parametrize(
        "optional,allows_prereleases",
        [(True, True), (True, False), (False, True), (False, False)],
    )
    def test_get_dependency_boolean_params(
        self, optional: bool, allows_prereleases: bool
    ) -> None:
        dependency = get_dependency(
            "test-package", optional=optional, allows_prereleases=allows_prereleases
        )
        assert dependency.is_optional() is optional
        assert dependency.allows_prereleases() is allows_prereleases


class TestCopyPath:
    @pytest.fixture
    def setup_files(self, tmp_path: Path) -> dict[str, Path]:
        # Create source file
        source_file = tmp_path / "source_file.txt"
        source_file.write_text("source content")

        # Create source directory with content
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("file1 content")
        (source_dir / "file2.txt").write_text("file2 content")

        # Create existing destination file
        dest_file = tmp_path / "dest_file.txt"
        dest_file.write_text("destination content")

        # Create existing destination directory with content
        dest_dir = tmp_path / "dest_dir"
        dest_dir.mkdir()
        (dest_dir / "existing.txt").write_text("existing content")

        return {
            "source_file": source_file,
            "source_dir": source_dir,
            "dest_file": dest_file,
            "dest_dir": dest_dir,
            "tmp_path": tmp_path,
        }

    def test_copy_file_to_new_destination(self, setup_files: dict[str, Path]) -> None:
        source = setup_files["source_file"]
        dest = setup_files["tmp_path"] / "new_file.txt"

        copy_path(source, dest)

        assert dest.exists()
        assert dest.read_text() == "source content"

    def test_copy_file_to_existing_file(self, setup_files: dict[str, Path]) -> None:
        source = setup_files["source_file"]
        dest = setup_files["dest_file"]

        copy_path(source, dest)

        assert dest.exists()
        assert dest.read_text() == "source content"

    def test_copy_file_to_existing_directory(
        self, setup_files: dict[str, Path]
    ) -> None:
        source = setup_files["source_file"]
        dest = setup_files["dest_dir"]

        copy_path(source, dest)

        assert dest.exists()
        assert dest.is_file()  # Directory is replaced with file
        assert dest.read_text() == "source content"

    def test_copy_directory_to_new_destination(
        self, setup_files: dict[str, Path]
    ) -> None:
        source = setup_files["source_dir"]
        dest = setup_files["tmp_path"] / "new_dir"

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "file1.txt").read_text() == "file1 content"
        assert (dest / "file2.txt").read_text() == "file2 content"

    def test_copy_directory_to_existing_directory(
        self, setup_files: dict[str, Path]
    ) -> None:
        source = setup_files["source_dir"]
        dest = setup_files["dest_dir"]

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "file1.txt").read_text() == "file1 content"
        assert (dest / "file2.txt").read_text() == "file2 content"
        assert not (dest / "existing.txt").exists()  # Old content is removed

    def test_copy_directory_to_existing_file(
        self, setup_files: dict[str, Path]
    ) -> None:
        source = setup_files["source_dir"]
        dest = setup_files["dest_file"]

        copy_path(source, dest)

        assert dest.is_dir()
        assert (dest / "file1.txt").read_text() == "file1 content"
        assert (dest / "file2.txt").read_text() == "file2 content"


class TestMockDulwichRepo:
    @pytest.fixture
    def repo_path(self, tmp_path: Path) -> Path:
        return tmp_path / "mock_repo"

    def test_init_with_path_object(self, repo_path: Path) -> None:
        repo_path.mkdir()
        repo = MockDulwichRepo(repo_path)
        assert repo.path == str(repo_path)

    def test_init_with_string_path(self, repo_path: Path) -> None:
        repo_path.mkdir()
        repo = MockDulwichRepo(str(repo_path))
        assert repo.path == str(repo_path)

    def test_head_returns_default_revision_encoded(self, repo_path: Path) -> None:
        repo_path.mkdir()
        repo = MockDulwichRepo(repo_path)
        expected = MOCK_DEFAULT_GIT_REVISION.encode()
        assert repo.head() == expected
        assert isinstance(repo.head(), bytes)

    def test_init_ignores_extra_kwargs(self, repo_path: Path) -> None:
        repo_path.mkdir()
        repo = MockDulwichRepo(repo_path, ignored_param="value", another_param=123)
        assert repo.path == str(repo_path)
        assert repo.head() == MOCK_DEFAULT_GIT_REVISION.encode()


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


class TestIsolatedEnvironment:
    def test_isolated_environment_restores_original_environ(self) -> None:
        original_environ = dict(os.environ)
        with isolated_environment():
            os.environ["TEST_VAR"] = "test"
        assert os.environ == original_environ

    def test_isolated_environment_clears_environ(self) -> None:
        os.environ["TEST_VAR"] = "test"
        with isolated_environment(clear=True):
            assert "TEST_VAR" not in os.environ
        assert "TEST_VAR" in os.environ

    def test_isolated_environment_updates_environ(self) -> None:
        with isolated_environment(environ={"NEW_VAR": "new_value"}):
            assert os.environ["NEW_VAR"] == "new_value"
        assert "NEW_VAR" not in os.environ

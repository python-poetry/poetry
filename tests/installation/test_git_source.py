from __future__ import annotations

import json

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.package import Package

from poetry.installation.git_source import EditableGitSource


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def _package() -> Package:
    return Package(
        "example",
        "1.0",
        source_type="git",
        source_url="https://user:secret@git.example/org/repository.git",
        source_reference="main",
        source_resolved_reference="a" * 40,
        develop=True,
    )


def test_checkout_identity(tmp_path: Path) -> None:
    sources = EditableGitSource(tmp_path)
    first = _package()
    paths = {sources.path_for(first)}
    for attribute, value in [
        ("_source_url", "https://git.example/other/repository.git"),
        ("_source_resolved_reference", "b" * 40),
        ("_source_subdirectory", "another-project"),
    ]:
        package = first.clone()
        setattr(package, attribute, value)
        paths.add(sources.path_for(package))
    assert len(paths) == 4
    assert all("secret" not in str(path) and "user" not in path.name for path in paths)
    assert sources.path_for(first.clone()) == sources.path_for(first)


@pytest.mark.parametrize("marker", [None, "not json", '{"package": "other"}'])
def test_unmanaged_checkout_is_not_replaced(
    tmp_path: Path, mocker: MockerFixture, marker: str | None
) -> None:
    sources = EditableGitSource(tmp_path)
    package = _package()
    path = sources.path_for(package)
    path.mkdir(parents=True)
    if marker is not None:
        path.with_name(path.name + ".json").write_text(marker, encoding="utf-8")
    clone = mocker.patch("poetry.installation.git_source.Git.clone")
    with pytest.raises(RuntimeError, match="unmanaged"):
        sources.prepare(package)
    sources.remove(package)
    assert path.is_dir()
    clone.assert_not_called()


@pytest.mark.parametrize("source_type", ["git", "directory"])
def test_uninstall_does_not_remove_external_editable_directory(
    tmp_path: Path, source_type: str
) -> None:
    external = tmp_path / "outside"
    external.mkdir()
    package = _package()
    package._source_type = source_type
    package._source_url = str(external)
    EditableGitSource(tmp_path / "environment").remove(package)
    assert external.is_dir()


def test_checkout_symlink_does_not_grant_ownership(tmp_path: Path) -> None:
    sources = EditableGitSource(tmp_path / "environment")
    package = _package()
    checkout = sources.path_for(package)
    checkout.parent.mkdir(parents=True)
    external = tmp_path / "outside"
    external.mkdir()
    checkout.symlink_to(external, target_is_directory=True)
    checkout.with_name(checkout.name + ".json").write_text(
        json.dumps({"package": package.name}), encoding="utf-8"
    )
    package._source_url = str(checkout)
    sources.remove(package)
    assert external.is_dir()
    assert checkout.is_symlink()


def test_symlinked_source_root_outside_environment_is_rejected(tmp_path: Path) -> None:
    environment = tmp_path / "environment"
    environment.mkdir()
    external = tmp_path / "outside"
    external.mkdir()
    (environment / "src").symlink_to(external, target_is_directory=True)
    with pytest.raises(RuntimeError, match="outside the environment"):
        EditableGitSource(environment).prepare(_package())
    assert list(external.iterdir()) == []


def test_failed_clone_removes_only_new_checkout(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    sources = EditableGitSource(tmp_path)
    package = _package()
    path = sources.path_for(package)

    def clone(**kwargs: object) -> None:
        path.mkdir(parents=True)
        raise RuntimeError("interrupted clone")

    mocker.patch("poetry.installation.git_source.Git.clone", side_effect=clone)
    with pytest.raises(RuntimeError, match="interrupted clone"):
        sources.prepare(package)
    assert not path.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_marker_failure_preserves_existing_ownership(
    tmp_path: Path, mocker: MockerFixture, existing: bool
) -> None:
    sources = EditableGitSource(tmp_path)
    package = _package()
    path = sources.path_for(package)
    marker = path.with_name(path.name + ".json")

    def clone(**kwargs: object) -> None:
        path.mkdir(parents=True, exist_ok=True)

    mocker.patch("poetry.installation.git_source.Git.clone", side_effect=clone)
    if existing:
        sources.prepare(package)
    # atomic_open uses os.replace, so a failed replacement must keep the old marker.
    mocker.patch(
        "requests.utils.os.replace",
        side_effect=OSError("interrupted marker replacement"),
    )
    with pytest.raises(OSError, match="interrupted marker replacement"):
        sources.prepare(package)
    assert path.exists() == existing
    assert marker.exists() == existing
    if existing:
        assert json.loads(marker.read_text(encoding="utf-8"))["package"] == package.name

from __future__ import annotations

import csv

from pathlib import Path

import pytest

from poetry.installation.uninstaller import StashedUninstallPathSet
from poetry.installation.uninstaller import UninstallPathSet
from poetry.installation.uninstaller import _normalize_path
from poetry.installation.uninstaller import _uninstallation_paths
from poetry.installation.uninstaller import compress_for_rename
from poetry.installation.uninstaller import uninstall_distribution
from poetry.utils._compat import WINDOWS
from poetry.utils.env import MockEnv


def _make_env(tmp_path: Path) -> MockEnv:
    env_path = tmp_path / "env"
    env_path.mkdir()
    purelib = env_path / "purelib"
    purelib.mkdir()
    scripts = env_path / "scripts"
    scripts.mkdir()
    env = MockEnv(path=env_path, is_venv=True, sys_path=[str(purelib)])
    env.paths["purelib"] = str(purelib)
    env.paths["platlib"] = str(purelib)
    env.paths["scripts"] = str(scripts)
    env.set_paths()
    return env


def _install_fake_distribution(
    env: MockEnv,
    name: str = "demo",
    version: str = "1.0.0",
    *,
    with_script: bool = True,
    extra_files: list[tuple[str, str]] | None = None,
    extra_symlinked_dirs: list[str] | None = None,
) -> tuple[Path, list[Path]]:
    """Create a fake installed distribution under env's purelib.

    Returns ``(dist_info_dir, installed_paths)``.
    """
    purelib = Path(env.paths["purelib"])
    scripts = Path(env.paths["scripts"])

    pkg_dir = purelib / name
    pkg_dir.mkdir()
    init_py = pkg_dir / "__init__.py"
    init_py.write_text(f"# {name}\n", encoding="utf-8")
    module_py = pkg_dir / "module.py"
    module_py.write_text("x = 1\n", encoding="utf-8")

    dist_info = purelib / f"{name}-{version}.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n", encoding="utf-8"
    )
    (dist_info / "INSTALLER").write_text("Poetry\n", encoding="utf-8")

    installed: list[Path] = [init_py, module_py]
    record_rows = [
        (f"{name}/__init__.py", "", ""),
        (f"{name}/module.py", "", ""),
        (f"{name}-{version}.dist-info/METADATA", "", ""),
        (f"{name}-{version}.dist-info/INSTALLER", "", ""),
    ]

    if with_script:
        script_path = scripts / f"{name}-cli"
        script_path.write_text("#!/usr/bin/env python\nprint('hi')\n", encoding="utf-8")
        installed.append(script_path)
        entry_points = dist_info / "entry_points.txt"
        entry_points.write_text(
            f"[console_scripts]\n{name}-cli = {name}.module:main\n", encoding="utf-8"
        )
        record_rows.append((f"{name}-{version}.dist-info/entry_points.txt", "", ""))
        record_rows.append((f"../scripts/{name}-cli", "", ""))

    if extra_files:
        for relpath, content in extra_files:
            target = purelib / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            installed.append(target)
            record_rows.append((relpath, "", ""))

    if extra_symlinked_dirs:
        link_target = purelib / f"{name}-symlink-target"
        link_target.mkdir(exist_ok=True)
        for relpath in extra_symlinked_dirs:
            link = purelib / relpath
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(link_target, target_is_directory=True)
            except OSError:
                if WINDOWS:
                    pytest.skip(
                        "Symlink creation requires privileges or developer mode"
                        " on Windows."
                    )
                raise
            installed.append(link)
            record_rows.append((relpath, "", ""))

    record_path = dist_info / "RECORD"
    with record_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        for row in record_rows:
            writer.writerow(row)
        writer.writerow((f"{name}-{version}.dist-info/RECORD", "", ""))

    installed.append(dist_info)
    return dist_info, installed


def test_uninstall_distribution_removes_files(tmp_path: Path) -> None:
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env)

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None
    pathset.commit()

    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    assert not dist_info.exists()


def test_uninstall_distribution_returns_none_when_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = _make_env(tmp_path)
    pathset = uninstall_distribution(env, "ghost")
    assert pathset is None
    assert any("ghost" in record.message for record in caplog.records)


def test_uninstall_distribution_refuses_dist_outside_env(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Build a normal env, then point purelib at a location outside env.path so
    # the discovered dist fails the env-prefix guard in uninstall_distribution.
    env = _make_env(tmp_path)
    elsewhere = tmp_path / "elsewhere" / "site-packages"
    elsewhere.mkdir(parents=True)
    env.paths["purelib"] = str(elsewhere)
    env.paths["platlib"] = str(elsewhere)

    dist_info, installed = _install_fake_distribution(env, with_script=False)

    pathset = uninstall_distribution(env, "demo")

    assert pathset is None
    assert dist_info.exists()
    for path in installed:
        assert path.exists()
    assert any("outside environment" in r.message for r in caplog.records)


def test_uninstall_distribution_refuses_dist_in_stdlib(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)
    # Make the stdlib guard trip by claiming purelib IS the stdlib.
    env.paths["stdlib"] = env.paths["purelib"]

    pathset = uninstall_distribution(env, "demo")

    assert pathset is None
    assert dist_info.exists()
    for path in installed:
        assert path.exists()
    assert any("standard library" in r.message for r in caplog.records)


def test_uninstall_distribution_refuses_dist_without_record(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)
    # Remove RECORD so importlib.metadata reports dist.files as None.
    (dist_info / "RECORD").unlink()

    pathset = uninstall_distribution(env, "demo")

    assert pathset is None
    assert dist_info.exists()
    for path in installed:
        assert path.exists()
    assert any("RECORD file is missing" in r.message for r in caplog.records)


def test_uninstall_distribution_does_not_match_prefix_sibling(
    tmp_path: Path,
) -> None:
    # env.path = "<tmp>/env"; a sibling directory "<tmp>/env-sibling/..."
    # must not be treated as inside the env just because its absolute path
    # startswith env.path. Exercises the os.sep guard in _permitted().
    env = _make_env(tmp_path)
    _install_fake_distribution(env, with_script=False)

    # Create a sibling directory next to env.path that shares a name prefix.
    sibling_root = env.path.with_name(env.path.name + "-sibling")
    sibling_root.mkdir()
    stray = sibling_root / "stray.py"
    stray.write_text("# outside, but env.path is a prefix string\n", encoding="utf-8")

    dist = next(iter(env.site_packages.distributions(name="demo")))
    pathset = UninstallPathSet(dist, env.path)
    pathset.add(str(stray))

    # The sibling-path must be refused, not added for removal.
    assert not any(str(stray) in p for p in pathset.paths)
    assert pathset.refused == {_normalize_path(stray)}


def test_uninstall_distribution_collects_console_script(tmp_path: Path) -> None:
    env = _make_env(tmp_path)
    _install_fake_distribution(env, with_script=True)

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    scripts_dir = env.paths["scripts"]
    assert any(p.startswith(_normalize_path(scripts_dir)) for p in pathset.paths)

    pathset.commit()
    assert not (Path(scripts_dir) / "demo-cli").exists()


def test_rollback_restores_files(tmp_path: Path) -> None:
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(env)

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    for path in installed:
        if path.is_file():
            assert not path.exists()

    pathset.rollback()

    for path in installed:
        assert path.exists(), f"{path} should have been restored"


def test_refuses_paths_outside_env_prefix(tmp_path: Path) -> None:
    env = _make_env(tmp_path)
    _install_fake_distribution(env)

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "stray.py"
    outside_file.write_text("# outside\n", encoding="utf-8")

    dist = next(iter(env.site_packages.distributions(name="demo")))
    dist_parent = dist._path.parent  # type: ignore[attr-defined]
    pathset = UninstallPathSet(dist, env.path)
    assert dist.files
    for path in _uninstallation_paths(dist.files, dist_parent):
        pathset.add(path)
    pathset.add(str(outside_file))

    assert all("demo" in p for p in pathset.paths)
    assert pathset.refused == {_normalize_path(outside_file)}

    pathset.remove()
    pathset.commit()
    assert outside_file.exists(), "files outside the env prefix must not be removed"


def test_uninstall_distribution_with_symlinked_directory(tmp_path: Path) -> None:
    # A RECORD that lists a symlink to a directory is what makes subtracting
    # all_subdirs in compress_for_rename() relevant.
    # Without it, remove() stashes the whole package dir first and then
    # raises FileNotFoundError trying to stash the now-missing symlink.
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(
        env, with_script=False, extra_symlinked_dirs=["demo/datalink"]
    )

    purelib = Path(env.paths["purelib"])
    link = purelib / "demo" / "datalink"
    link_target = purelib / "demo-symlink-target"
    assert link.is_symlink()
    assert link_target.is_dir()

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None
    pathset.commit()

    assert not (purelib / "demo").exists()
    assert not link.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    # The symlink is removed, but its target directory must be left untouched —
    # the uninstaller removes links, not the things they point at.
    assert link_target.is_dir()


def test_stashed_path_set_stashes_and_rolls_back_individual_file(
    tmp_path: Path,
) -> None:
    # When stashing a regular file (not a whole directory), stash() goes
    # through _get_file_stash, which allocates a TempDirectory per parent
    # and computes a relpath inside it. A second file under the same parent
    # reuses the previously-allocated TempDirectory (the break branch in
    # _get_file_stash). Verify the round-trip for both.
    target_dir = tmp_path / "site"
    target_dir.mkdir()
    file_a = target_dir / "a.txt"
    file_a.write_text("AAA", encoding="utf-8")
    file_b = target_dir / "b.txt"
    file_b.write_text("BBB", encoding="utf-8")
    sibling = target_dir / "sibling.txt"
    sibling.write_text("untouched", encoding="utf-8")

    stashed = StashedUninstallPathSet()
    new_path_a = stashed.stash(str(file_a))
    new_path_b = stashed.stash(str(file_b))

    assert not file_a.exists()
    assert not file_b.exists()
    assert Path(new_path_a).read_text() == "AAA"
    assert Path(new_path_b).read_text() == "BBB"
    # Both files share the same stash root (the existing save_dir is reused).
    assert Path(new_path_a).parent == Path(new_path_b).parent
    # Stashing files must not touch unrelated siblings in the same directory.
    assert sibling.exists()
    assert sibling.read_text() == "untouched"
    assert stashed.can_rollback

    stashed.rollback()

    assert file_a.exists() and file_a.read_text() == "AAA"
    assert file_b.exists() and file_b.read_text() == "BBB"
    assert sibling.exists()
    assert not stashed.can_rollback


def test_compress_for_rename_collapses_full_directory(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f1.touch()
    f2 = pkg / "b.py"
    f2.touch()

    result = compress_for_rename([str(f1), str(f2)])
    assert any(r.rstrip("/\\").endswith("pkg") for r in result)

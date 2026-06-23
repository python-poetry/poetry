from __future__ import annotations

import csv
import os
import platform
import shutil

from importlib.util import cache_from_source
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.installation.uninstaller import UninstallPathSet
from poetry.installation.uninstaller import _normalize_path
from poetry.installation.uninstaller import uninstall_distribution
from poetry.utils._compat import WINDOWS
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
        # create another file to ensure the directory is not empty (more realistic)
        (scripts / "python").touch()
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
    with record_path.open("w", newline="", encoding="utf-8") as fh:
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

    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    assert not dist_info.exists()


def test_uninstall_distribution_removes_entire_dist_info(tmp_path: Path) -> None:
    # The .dist-info directory belongs solely to one distribution, so it is
    # removed whole - including files an installer added without listing them in
    # RECORD (e.g. direct_url.json), which the per-file removal would leave
    # behind (orphaning the .dist-info directory).
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)
    unlisted = dist_info / "direct_url.json"
    unlisted.write_text("{}", encoding="utf-8")

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    # The unlisted file is not discovered for removal ...
    assert not any("direct_url.json" in p for p in pathset.paths)
    # ... but the whole .dist-info directory is gone anyway.
    assert not unlisted.exists()
    assert not dist_info.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"


def test_uninstall_distribution_tolerates_already_removed_dist_info(
    tmp_path: Path,
) -> None:
    # If the .dist-info directory has vanished by the time it is removed (e.g. a
    # concurrent removal, or an entry disappearing mid-walk), the uninstall must
    # complete without error rather than leaving things half-done.
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)

    dist = next(iter(env.site_packages.distributions(name="demo")))
    dist_parent = dist._path.parent  # type: ignore[attr-defined]
    protected = {_normalize_path(p) for p in env.paths.values() if p}
    protected.add(_normalize_path(env.path))
    pathset = UninstallPathSet(dist, env.path, protected_dirs=protected)
    assert dist.files
    for entry in dist.files:
        pathset.add(os.path.join(dist_parent, entry))

    # Drop the .dist-info directory out from under remove().
    shutil.rmtree(dist_info)

    pathset.remove()  # must not raise

    for path in installed:
        assert not path.exists(), f"{path} should have been removed"


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
    scripts_dir = Path(env.paths["scripts"])
    demo_script = scripts_dir / "demo-cli"
    assert demo_script.exists()

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    assert any(p.startswith(_normalize_path(scripts_dir)) for p in pathset.paths)

    assert scripts_dir.exists()
    assert not demo_script.exists()


@pytest.mark.skipif(
    WINDOWS or platform.system() == "FreeBSD",
    reason="chmod does not prevent deletion on Windows and FreeBSD",
)
def test_uninstall_distribution_removes_dist_info_last_and_is_rerunnable(
    tmp_path: Path,
) -> None:
    # If a file cannot be removed, the uninstall raises and the .dist-info
    # directory (with its RECORD) is left intact so the user can re-trigger the
    # uninstall. Make module.py unremovable by making its parent read-only.
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)

    purelib = Path(env.paths["purelib"])
    pkg_dir = purelib / "demo"

    # Drop write permission on the package dir so removing files inside fails.
    pkg_dir.chmod(0o500)
    try:
        with pytest.raises(OSError):
            uninstall_distribution(env, "demo")
    finally:
        pkg_dir.chmod(0o700)

    # The .dist-info directory (and RECORD) must survive so the uninstall can be
    # triggered again.
    assert dist_info.exists()
    assert (dist_info / "RECORD").exists()

    # Re-running now succeeds and removes everything.
    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    assert not dist_info.exists()


def test_uninstall_distribution_ignores_already_missing_file(tmp_path: Path) -> None:
    # A path listed in RECORD that is already gone from disk must not raise.
    env = _make_env(tmp_path)
    dist_info, installed = _install_fake_distribution(env, with_script=False)

    # Delete one recorded file before uninstalling.
    (Path(env.paths["purelib"]) / "demo" / "module.py").unlink()

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    assert not dist_info.exists()


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
    for entry in dist.files:
        pathset.add(os.path.join(dist_parent, entry))
    pathset.add(str(outside_file))

    assert all("demo" in p for p in pathset.paths)
    assert pathset.refused == {_normalize_path(outside_file)}

    pathset.remove()
    assert outside_file.exists(), "files outside the env prefix must not be removed"


def test_uninstall_distribution_with_symlinked_directory(tmp_path: Path) -> None:
    # A RECORD that lists a symlink to a directory must be unlinked (os.remove
    # removes the link, not its target), and the package dir is then rmdir'd
    # once empty. The link's target directory must be left untouched.
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

    assert not (purelib / "demo").exists()
    assert not link.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    # The symlink is removed, but its target directory must be left untouched —
    # the uninstaller removes links, not the things they point at.
    assert link_target.is_dir()


def test_uninstall_distribution_prunes_empty_namespace_dirs(tmp_path: Path) -> None:
    # A namespace-style layout whose only files live in a deep leaf (no
    # __init__.py in the intermediate dirs). Removing the leaf files must prune
    # the now-empty intermediate directories by climbing upward, while a sibling
    # package sharing the namespace - and the site-packages root - survive.
    env = _make_env(tmp_path)
    purelib = Path(env.paths["purelib"])

    # Sibling package under the same top-level namespace that is NOT uninstalled.
    sibling = purelib / "ns" / "sibling"
    sibling.mkdir(parents=True)
    (sibling / "__init__.py").write_text("# sibling\n", encoding="utf-8")

    _, installed = _install_fake_distribution(
        env,
        with_script=False,
        extra_files=[("ns/cloud/demo/leaf.py", "x = 1\n")],
    )

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    # The emptied intermediate dirs are pruned ...
    assert not (purelib / "ns" / "cloud").exists()
    # ... but the namespace root survives because the sibling package remains,
    # and site-packages itself is never removed.
    assert sibling.exists()
    assert (purelib / "ns").is_dir()
    assert purelib.is_dir()


def test_prune_empty_dirs_tolerates_already_removed_dir(tmp_path: Path) -> None:
    # Updates run in parallel, so two builtin uninstalls can prune a shared
    # namespace directory concurrently. Pruning one that another uninstall has
    # already removed must not raise - rmdir's OSError is swallowed and the
    # climb simply stops.
    env = _make_env(tmp_path)
    _install_fake_distribution(env, with_script=False)
    dist = next(iter(env.site_packages.distributions(name="demo")))

    protected = {_normalize_path(p) for p in env.paths.values() if p}
    protected.add(_normalize_path(env.path))
    pathset = UninstallPathSet(dist, env.path, protected_dirs=protected)

    purelib = Path(env.paths["purelib"])
    # A nested namespace dir that is never created on disk (as if a concurrent
    # uninstall already removed it), still inside the env prefix.
    gone = _normalize_path(purelib / "ns" / "cloud")

    pathset._prune_empty_dirs({gone})  # must not raise


def test_uninstall_distribution_keeps_directory_with_unrelated_file(
    tmp_path: Path,
) -> None:
    # A stray file that is not part of the distribution (not in RECORD) and
    # shares the package directory must survive: rmdir refuses to remove the
    # non-empty directory out from under it.
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(env, with_script=False)

    purelib = Path(env.paths["purelib"])
    stray = purelib / "demo" / "stray.txt"
    stray.write_text("not ours\n", encoding="utf-8")

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    # Every recorded file (and the .dist-info directory) is gone ...
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"
    # ... but the package directory survives because of the unrelated file.
    assert stray.exists()
    assert (purelib / "demo").is_dir()


def test_uninstall_distribution_removes_pycache_bytecode(tmp_path: Path) -> None:
    # Compiled bytecode in __pycache__ is discovered and removed along with the
    # package even when it is not listed in RECORD (it is often compiled lazily
    # on first import).
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(env, with_script=False)

    purelib = Path(env.paths["purelib"])
    module_py = purelib / "demo" / "module.py"
    pyc = Path(cache_from_source(str(module_py)))
    pyc.parent.mkdir(parents=True, exist_ok=True)
    pyc.write_bytes(b"\x00\x00\x00\x00")

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    # The bytecode was discovered for removal (it is not listed in RECORD) ...
    assert any(Path(p).name == pyc.name for p in pathset.paths)
    # ... and is gone from disk, along with its __pycache__ directory.
    assert not pyc.exists()
    assert not pyc.parent.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"


def test_uninstall_distribution_removes_bytecode_for_other_python_versions(
    tmp_path: Path,
) -> None:
    # The target environment may have been built with a different Python version
    # than the interpreter running Poetry, so __pycache__ holds bytecode tagged
    # for that version. All such cache files must be removed - not just the
    # current interpreter's cache_from_source() tag - and none of them are
    # listed in RECORD.
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(env, with_script=False)

    purelib = Path(env.paths["purelib"])
    pycache = purelib / "demo" / "__pycache__"
    pycache.mkdir()
    # Foreign version tags (not the interpreter running the tests) plus an
    # optimized variant and a cache file for a second source module.
    foreign_pycs = [
        pycache / "module.cpython-38.pyc",
        pycache / "module.cpython-313.pyc",
        pycache / "module.cpython-313.opt-1.pyc",
        pycache / "__init__.cpython-38.pyc",
    ]
    for pyc in foreign_pycs:
        pyc.write_bytes(b"\x00\x00\x00\x00")

    # A bytecode file whose stem does not match any source module must be left
    # alone - it does not belong to this distribution.
    unrelated_pyc = pycache / "other.cpython-38.pyc"
    unrelated_pyc.write_bytes(b"\x00\x00\x00\x00")

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    discovered = {Path(p).name for p in pathset.paths}
    for pyc in foreign_pycs:
        assert pyc.name in discovered, f"{pyc.name} should have been discovered"
        assert not pyc.exists()
    assert unrelated_pyc.name not in discovered
    assert unrelated_pyc.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"


def test_uninstall_distribution_scans_each_pycache_once(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    # add() runs for every .py file, but all .py files in one directory share a
    # single __pycache__. The listing must be memoized so the directory is
    # scanned once, not once per file.
    env = _make_env(tmp_path)
    extra_modules = [(f"demo/mod{i}.py", f"x = {i}\n") for i in range(5)]
    _, installed = _install_fake_distribution(
        env, with_script=False, extra_files=extra_modules
    )

    purelib = Path(env.paths["purelib"])
    pycache = purelib / "demo" / "__pycache__"
    pycache.mkdir()
    (pycache / "module.cpython-38.pyc").write_bytes(b"\x00\x00\x00\x00")

    listdir_spy = mocker.patch(
        "poetry.installation.uninstaller.os.listdir", wraps=os.listdir
    )

    pathset = uninstall_distribution(env, "demo")
    assert pathset is not None

    pycache_calls = [
        call
        for call in listdir_spy.call_args_list
        if str(call.args[0]).endswith("__pycache__")
    ]
    # demo/ holds 7 .py files (__init__, module, mod0..mod4) but only one
    # __pycache__, which must be listed exactly once.
    assert len(pycache_calls) == 1
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"


def test_uninstall_distribution_defers_directory_entry_in_record(
    tmp_path: Path,
) -> None:
    # If an entry listed in RECORD is a directory instead of a file
    # (which should actually not happen) os.remove() must not raise
    # out of the uninstall: the entry is deferred and removed
    # with rmdir once the files inside it are gone.
    env = _make_env(tmp_path)
    _, installed = _install_fake_distribution(env, with_script=False)

    purelib = Path(env.paths["purelib"])
    empty_dir = purelib / "demo" / "emptysub"
    empty_dir.mkdir()

    dist = next(iter(env.site_packages.distributions(name="demo")))
    dist_parent = dist._path.parent  # type: ignore[attr-defined]
    pathset = UninstallPathSet(dist, env.path)
    assert dist.files
    for record_path in dist.files:
        pathset.add(os.path.join(dist_parent, record_path))
    # Inject the directory path as if RECORD had listed it.
    pathset.add(str(empty_dir))
    assert _normalize_path(empty_dir) in pathset.paths

    pathset.remove()  # must not raise

    assert not empty_dir.exists()
    for path in installed:
        assert not path.exists(), f"{path} should have been removed"

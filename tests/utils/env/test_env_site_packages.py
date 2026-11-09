from __future__ import annotations

import uuid

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.utils._compat import WINDOWS
from poetry.utils.env import SitePackages


if TYPE_CHECKING:
    from importlib import metadata

    from pytest_mock import MockerFixture


def test_env_site_simple(tmp_path: Path, mocker: MockerFixture) -> None:
    # emulate permission error when creating directory
    mocker.patch("pathlib.Path.mkdir", side_effect=OSError())
    site_packages = SitePackages(Path("/non-existent"), fallbacks=[tmp_path])
    candidates = site_packages.make_candidates(Path("hello.txt"), writable_only=True)
    hello = tmp_path / "hello.txt"

    assert len(candidates) == 1
    assert candidates[0].as_posix() == hello.as_posix()

    content = str(uuid.uuid4())
    site_packages.write_text(Path("hello.txt"), content, encoding="utf-8")

    assert hello.read_text(encoding="utf-8") == content

    assert not (site_packages.path / "hello.txt").exists()


def test_env_site_select_first(tmp_path: Path) -> None:
    fallback = tmp_path / "fallback"
    fallback.mkdir(parents=True)

    site_packages = SitePackages(tmp_path, fallbacks=[fallback])
    candidates = site_packages.make_candidates(Path("hello.txt"), writable_only=True)

    assert len(candidates) == 2
    assert len(site_packages.find(Path("hello.txt"))) == 0

    content = str(uuid.uuid4())
    site_packages.write_text(Path("hello.txt"), content, encoding="utf-8")

    assert (site_packages.path / "hello.txt").exists()
    assert not (fallback / "hello.txt").exists()

    assert len(site_packages.find(Path("hello.txt"))) == 1


class TestDistributionFiles:
    """Regression tests for importlib.metadata.Distribution.files.

    Poetry relies on Distribution.files to contain all files, as listed in its RECORD.

    Distribution.files is known to be unreliable on Windows with Python 3.10/3.11
    when RECORD contains absolute paths
    -- see https://github.com/python/importlib_metadata/issues/535.
    """

    @staticmethod
    def _build_distribution(
        site_packages: Path, record_entries: list[str]
    ) -> metadata.Distribution:
        """Create a ``foo-1.0.dist-info/RECORD`` under ``site_packages`` listing the given raw
        RECORD path entries and return the corresponding distribution.

        The distribution is obtained via ``SitePackages.distributions()`` -- i.e. through the
        same discovery path Poetry actually uses -- rather than constructed directly. That way an
        ``importlib_metadata`` Distribution can be returned instead of an ``importlib.metadata``
        one if the backport is installed, which is exactly the scenario this guards against.

        Each entry is written as ``<entry>,,`` (no hash/size). The caller must materialize the
        referenced files on disk first -- ``Distribution.files`` filters out entries whose target
        does not exist.
        """
        dist_info = site_packages / "foo-1.0.dist-info"
        dist_info.mkdir(parents=True, exist_ok=True)
        record_lines = [*record_entries, "foo-1.0.dist-info/RECORD"]
        (dist_info / "RECORD").write_text(
            "".join(f"{entry},,\n" for entry in record_lines), encoding="utf-8"
        )
        distribution = SitePackages(site_packages).find_distribution("foo")
        assert distribution is not None
        return distribution

    @staticmethod
    def _resolved_files(distribution: metadata.Distribution) -> set[Path]:
        """Resolve every entry of ``Distribution.files`` through ``locate_file`` to an absolute
        path, mirroring how Poetry consumes them."""
        resolved = set()
        for file in distribution.files or []:
            located = distribution.locate_file(file)
            assert isinstance(located, Path)
            resolved.add(located.resolve())
        return resolved

    def test_distribution_files_relative_paths(self, tmp_path: Path) -> None:
        site_packages = tmp_path / "venv" / "site-packages"
        relative_entries = ["foo/__init__.py", "foo/sub/bar.py"]

        expected = set()
        for entry in relative_entries:
            target = site_packages / Path(entry)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            expected.add(target.resolve())

        distribution = self._build_distribution(site_packages, relative_entries)

        assert expected <= self._resolved_files(distribution)

    def test_distribution_files_absolute_path(self, tmp_path: Path) -> None:
        site_packages = tmp_path / "venv" / "site-packages"
        external = tmp_path / "external" / "data.bin"
        external.parent.mkdir(parents=True)
        external.write_text("", encoding="utf-8")

        distribution = self._build_distribution(site_packages, [str(external)])

        assert external.resolve() in self._resolved_files(distribution)

    def test_distribution_files_script_relative_path(self, tmp_path: Path) -> None:
        venv = tmp_path / "venv"
        site_packages = venv / "site-packages"
        scripts = venv / ("Scripts" if WINDOWS else "bin")
        script = scripts / "foo"
        scripts.mkdir(parents=True)
        script.write_text("", encoding="utf-8")

        # Console scripts are recorded relative to site-packages with a ".." traversal.
        distribution = self._build_distribution(
            site_packages, [f"../{scripts.name}/foo"]
        )

        assert script.resolve() in self._resolved_files(distribution)

    def test_distribution_files_script_absolute_path(self, tmp_path: Path) -> None:
        venv = tmp_path / "venv"
        site_packages = venv / "site-packages"
        scripts = venv / ("Scripts" if WINDOWS else "bin")
        script = scripts / "foo"
        scripts.mkdir(parents=True)
        script.write_text("", encoding="utf-8")

        distribution = self._build_distribution(site_packages, [str(script)])

        assert script.resolve() in self._resolved_files(distribution)

    @pytest.mark.skipif(not WINDOWS, reason="Windows path separators")
    @pytest.mark.parametrize("sep", ["/", "\\"])
    @pytest.mark.parametrize("kind", ["package", "script", "absolute"])
    def test_distribution_files_windows_separators(
        self, tmp_path: Path, kind: str, sep: str
    ) -> None:
        venv = tmp_path / "venv"
        site_packages = venv / "site-packages"

        if kind == "package":
            target = site_packages / "foo" / "bar.py"
            target.parent.mkdir(parents=True)
            target.write_text("", encoding="utf-8")
            entry = sep.join(("foo", "bar.py"))
        elif kind == "absolute":
            target = venv / "Scripts" / "foo.exe"
            target.parent.mkdir(parents=True)
            target.write_text("", encoding="utf-8")
            # Same absolute path spelled with native backslashes or with forward slashes.
            entry = str(target) if sep == "\\" else target.as_posix()
        else:  # script: relative ".." traversal into the Scripts directory
            target = venv / "Scripts" / "foo.exe"
            target.parent.mkdir(parents=True)
            target.write_text("", encoding="utf-8")
            entry = sep.join(("..", "Scripts", "foo.exe"))

        distribution = self._build_distribution(site_packages, [entry])

        assert target.resolve() in self._resolved_files(distribution)

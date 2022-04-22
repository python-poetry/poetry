from __future__ import annotations

import uuid

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.utils._compat import decode
from poetry.utils.env import SitePackages


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_env_site_simple(tmp_dir: str, mocker: MockerFixture):
    # emulate permission error when creating directory
    mocker.patch("pathlib.Path.mkdir", side_effect=OSError())
    site_packages = SitePackages(Path("/non-existent"), fallbacks=[Path(tmp_dir)])
    candidates = site_packages.make_candidates(Path("hello.txt"), writable_only=True)
    hello = Path(tmp_dir) / "hello.txt"

    assert len(candidates) == 1
    assert candidates[0].as_posix() == hello.as_posix()

    content = decode(str(uuid.uuid4()))
    site_packages.write_text(Path("hello.txt"), content, encoding="utf-8")

    assert hello.read_text(encoding="utf-8") == content

    assert not (site_packages.path / "hello.txt").exists()


def test_env_site_select_first(tmp_dir: str):
    path = Path(tmp_dir)
    fallback = path / "fallback"
    fallback.mkdir(parents=True)

    site_packages = SitePackages(path, fallbacks=[fallback])
    candidates = site_packages.make_candidates(Path("hello.txt"), writable_only=True)

    assert len(candidates) == 2
    assert len(site_packages.find(Path("hello.txt"))) == 0

    content = decode(str(uuid.uuid4()))
    site_packages.write_text(Path("hello.txt"), content, encoding="utf-8")

    assert (site_packages.path / "hello.txt").exists()
    assert not (fallback / "hello.txt").exists()

    assert len(site_packages.find(Path("hello.txt"))) == 1

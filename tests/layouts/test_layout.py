from pathlib import Path

import pytest

from poetry.layouts.layout import Layout

from pathlib import Path

from poetry.layouts.layout import Layout


class DummyLayout(Layout):
    def __init__(self, *args, basedir: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self._basedir = basedir

    @property
    def basedir(self) -> Path:
        return self._basedir


def test_readme_key_removed_if_readme_missing(tmp_path: Path) -> None:
    layout = DummyLayout(
        project="demo_project",
        readme_format="md",
        basedir=tmp_path,
    )

    content = layout.generate_project_content()
    project = content["project"]

    assert "readme" not in project


def test_readme_key_present_if_readme_exists(tmp_path: Path) -> None:
    (tmp_path / "README.md").touch()

    layout = DummyLayout(
        project="demo_project",
        readme_format="md",
        basedir=tmp_path,
    )

    content = layout.generate_project_content()
    project = content["project"]

    assert project["readme"] == "README.md"

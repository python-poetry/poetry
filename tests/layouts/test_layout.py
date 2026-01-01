from pathlib import Path
import pytest

from poetry.layouts.layout import Layout


class DummyLayout(Layout):
    """Override basedir for testing purposes."""
    def __init__(self, basedir: Path, **kwargs):
        super().__init__(**kwargs)
        self._test_basedir = basedir

    @property
    def basedir(self) -> Path:
        return self._test_basedir


def test_readme_key_removed_if_readme_missing(tmp_path: Path) -> None:
    layout = DummyLayout(
        project="demo_project",
        readme_format="md",
        basedir=tmp_path,
    )

    content = layout.generate_project_content()
    # README.md does not exist, key should be removed
    assert "readme" not in content["project"]


def test_readme_key_present_if_readme_exists(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.touch()

    layout = DummyLayout(
        project="demo_project",
        readme_format="md",
        basedir=tmp_path,
    )

    content = layout.generate_project_content()
    # README.md exists, key should be present
    assert content["project"]["readme"] == "README.md"

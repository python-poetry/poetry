import pytest

from poetry.console.commands.build import BuildCommand
from poetry.core.masonry import builder
from poetry.utils._compat import Path


@pytest.fixture
def source_dir(tmp_path):  # type: (Path) -> Path
    yield Path(tmp_path.as_posix())


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("build")


class MockedBuilder:
    def __init__(self, *args, **kw):
        pass

    def build(self, *args, **kw):
        pass


@pytest.fixture
def poetry_with_lock_file(project_factory, fixture_dir):
    source = fixture_dir("lock")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        pyproject_content=pyproject_content, poetry_lock_content=poetry_lock_content,
    )


def test_build_without_lock(command_tester_factory, poetry_with_lock_file, monkeypatch):
    content_of_written_pyproject_toml = []
    monkeypatch.setattr(
        BuildCommand,
        "_write_pyproject_toml",
        lambda _, content: content_of_written_pyproject_toml.append(content),
    )
    monkeypatch.setattr(builder, "Builder", MockedBuilder)

    tester = command_tester_factory("build", poetry=poetry_with_lock_file)
    tester.execute()

    # pyproject.toml is not changed
    assert len(content_of_written_pyproject_toml) == 0


def test_build_with_lock(command_tester_factory, poetry_with_lock_file, monkeypatch):
    content_of_written_pyproject_toml = []
    monkeypatch.setattr(
        BuildCommand,
        "_write_pyproject_toml",
        lambda _, content: content_of_written_pyproject_toml.append(content),
    )
    monkeypatch.setattr(builder, "Builder", MockedBuilder)

    tester = command_tester_factory("build", poetry=poetry_with_lock_file)
    tester.execute("--lock")

    assert len(
        content_of_written_pyproject_toml[0]["tool"]["poetry"]["dependencies"]
    ) > len(content_of_written_pyproject_toml[1]["tool"]["poetry"]["dependencies"])
    assert content_of_written_pyproject_toml[0]["tool"]["poetry"]["dependencies"] == {
        "python": "^3.8",
        "sampleproject": ">=1.3.1",
        "certifi": "2020.6.20",
        "chardet": "3.0.4",
        "docker": "4.3.1",
        "idna": "2.10",
        "pywin32": "227",
        "requests": "2.24.0",
        "six": "1.15.0",
        "urllib3": "1.25.10",
        "websocket-client": "0.57.0",
    }
    assert content_of_written_pyproject_toml[1]["tool"]["poetry"]["dependencies"] == {
        "python": "^3.8",
        "sampleproject": ">=1.3.1",
    }

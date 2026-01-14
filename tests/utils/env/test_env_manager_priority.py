"""
Regression tests for Poetry issue #10610.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.conftest import Config


class TestEnvManagerGetPriority:
    """Test that in-project .venv takes priority over VIRTUAL_ENV env var."""

    @pytest.fixture
    def mock_virtual_env(self, mocker: MockerFixture) -> MagicMock:
        """Mock VirtualEnv to avoid system calls but preserve path."""

        def side_effect(path: Path | str, base: Path | str | None = None) -> MagicMock:
            m = MagicMock(spec=VirtualEnv)
            m.path = Path(str(path))
            return m

        return mocker.patch(
            "poetry.utils.env.env_manager.VirtualEnv", side_effect=side_effect
        )

    def test_get_returns_in_project_venv_when_virtual_env_is_set(
        self,
        poetry: Poetry,
        config: Config,
        mocker: MockerFixture,
        tmp_path: Path,
        mock_virtual_env: MagicMock,
    ) -> None:
        """
        When VIRTUAL_ENV is set (e.g., running via pipx) but an in-project
        .venv exists, EnvManager.get() should return the in-project venv.
        """
        config.merge({"virtualenvs": {"in-project": True}})

        project_dir = poetry.file.path.parent
        venv_path = project_dir / ".venv"
        venv_path.mkdir(parents=True, exist_ok=True)

        fake_pipx_venv = str(tmp_path / "pipx_venv")
        mocker.patch.dict(os.environ, {"VIRTUAL_ENV": fake_pipx_venv})

        manager = EnvManager(poetry)
        env = manager.get()

        assert env.path == venv_path
        assert str(env.path) != fake_pipx_venv
        assert str(env.path) != "."

    def test_get_returns_in_project_venv_when_virtual_env_is_dot(
        self,
        poetry: Poetry,
        config: Config,
        mocker: MockerFixture,
        mock_virtual_env: MagicMock,
    ) -> None:
        """
        When VIRTUAL_ENV is set to "." (current directory), but an in-project
        .venv exists, EnvManager.get() should return the in-project venv.
        """
        config.merge({"virtualenvs": {"in-project": True}})

        project_dir = poetry.file.path.parent
        venv_path = project_dir / ".venv"
        venv_path.mkdir(parents=True, exist_ok=True)

        mocker.patch.dict(os.environ, {"VIRTUAL_ENV": "."})

        manager = EnvManager(poetry)
        env = manager.get()

        assert str(env.path) != "."
        assert env.path == venv_path

    def test_get_after_env_use_returns_correct_path(
        self,
        poetry: Poetry,
        config: Config,
        mocker: MockerFixture,
        tmp_path: Path,
        mock_virtual_env: MagicMock,
    ) -> None:
        """
        After `poetry env use`, get() should return the newly created venv,
        not the VIRTUAL_ENV from the parent process.
        """
        config.merge({"virtualenvs": {"in-project": True}})

        project_dir = poetry.file.path.parent
        venv_path = project_dir / ".venv"
        venv_path.mkdir(parents=True, exist_ok=True)

        pipx_venv = str(tmp_path / "share/pipx/venvs/poetry")
        mocker.patch.dict(os.environ, {"VIRTUAL_ENV": pipx_venv})

        manager = EnvManager(poetry)

        env = manager.get(reload=True)

        assert env.path == venv_path
        assert str(env.path) != "."
        assert pipx_venv != str(env.path)

    def test_env_info_path_output_is_not_dot(
        self,
        poetry: Poetry,
        config: Config,
        mocker: MockerFixture,
        mock_virtual_env: MagicMock,
    ) -> None:
        """
        Verify that env.path when converted to string is never just ".".
        """
        config.merge({"virtualenvs": {"in-project": True}})

        project_dir = poetry.file.path.parent
        venv_path = project_dir / ".venv"
        venv_path.mkdir(parents=True, exist_ok=True)

        mocker.patch.dict(os.environ, {"VIRTUAL_ENV": "."})

        manager = EnvManager(poetry)
        env = manager.get()

        path_str = str(env.path)
        assert path_str != ".", "env.path should not be '.'"

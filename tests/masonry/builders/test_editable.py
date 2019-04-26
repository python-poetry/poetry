# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from poetry.io import NullIO
from poetry.masonry.builders import EditableBuilder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv

fixtures_dir = Path(__file__).parent / "fixtures"


def test_build_should_delegate_to_pip_for_non_pure_python_packages(tmp_dir, mocker):
    move = mocker.patch("shutil.move")
    tmp_dir = Path(tmp_dir)
    env = MockEnv(path=tmp_dir, pip_version="18.1", execute=False)
    env.site_packages.mkdir(parents=True)
    module_path = fixtures_dir / "extended"

    builder = EditableBuilder(Poetry.create(module_path), env, NullIO())
    builder.build()

    expected = [["python", "-m", "pip", "install", "-e", str(module_path)]]
    assert expected == env.executed

    assert 0 == move.call_count


def test_build_should_temporarily_remove_the_pyproject_file(tmp_dir, mocker):
    move = mocker.patch("shutil.move")
    tmp_dir = Path(tmp_dir)
    env = MockEnv(path=tmp_dir, pip_version="19.1", execute=False)
    env.site_packages.mkdir(parents=True)
    module_path = fixtures_dir / "extended"

    builder = EditableBuilder(Poetry.create(module_path), env, NullIO())
    builder.build()

    expected = [["python", "-m", "pip", "install", "-e", str(module_path)]]
    assert expected == env.executed

    assert 2 == move.call_count

    expected_calls = [
        mocker.call(
            str(module_path / "pyproject.toml"), str(module_path / "pyproject.tmp")
        ),
        mocker.call(
            str(module_path / "pyproject.tmp"), str(module_path / "pyproject.toml")
        ),
    ]

    assert expected_calls == move.call_args_list

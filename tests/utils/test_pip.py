import subprocess

import pytest

from poetry.utils.pip import pip_install


def test_pip_install_successful(tmp_dir, tmp_venv, fixture_dir):
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    result = pip_install(file_path, tmp_venv)

    assert "Successfully installed demo-0.1.0" in result


def test_pip_install_with_keyboard_interrupt(tmp_dir, tmp_venv, fixture_dir, mocker):
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        pip_install(file_path, tmp_venv)
    subprocess.run.assert_called_once()

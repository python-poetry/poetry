import os
import pytest
import sys


@pytest.mark.skipif(
    sys.platform == "win32", reason="Permissions are different on Windows"
)
def test_config_sets_the_proper_file_permissions(config):
    config.add_property("settings.virtualenvs.create", True)

    mode = oct(os.stat(str(config.file)).st_mode & 0o777)

    assert int(mode, 8) == 384


def test_config_add_property(config):
    config.add_property("settings.virtualenvs.create", True)

    content = config.file.read()
    assert content == {"settings": {"virtualenvs": {"create": True}}}

    config.remove_property("settings.virtualenvs.create")

    content = config.file.read()
    assert content == {"settings": {"virtualenvs": {}}}

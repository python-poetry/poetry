import pytest

from poetry.console.commands import RunCommand
from poetry.utils.env import Env


def test_run_script_sets_argv(app):
    """
    If RunCommand calls a script defined in pyproject.toml, sys.argv[0] should
    be set to the full path of the script.
    """

    def mock_foo(bin):
        return "/full/path/to/" + bin

    def mock_run(*args, **kwargs):
        return dict(args=args, kwargs=kwargs)

    command = app.find("run")
    command._env = Env.get()
    # fake the existence of our script
    command._env._bin = mock_foo
    # we don't want to run anything
    command._env.run = mock_run
    res = command.run_script("cli:cli", ["foogit", "status"])
    expected = dict(
        args=(
            "python",
            "-c",
            "\"import sys; from importlib import import_module; sys.argv = ['/full/path/to/foogit', 'status']; import_module('cli').cli()\"",
        ),
        kwargs={"call": True, "shell": True},
    )
    assert res == expected

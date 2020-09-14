import pytest

from clikit.args import ArgvArgs

from poetry.console.config import ApplicationConfig
from poetry.exceptions import PoetryException


def test_overwrite_exception_in_case_of_invalid_command(app):
    conf = ApplicationConfig()
    args = ArgvArgs(["poetry", "--vers"])

    with pytest.raises(PoetryException):
        conf.create_io(app, args)

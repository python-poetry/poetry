import pytest

from clikit.args import ArgvArgs

from poetry.console.config import ApplicationConfig
from poetry.exceptions import PoetryException


def test_overwrite_exception_in_case_of_invalid_command(app):
    conf = ApplicationConfig()
    args = ArgvArgs(["poetry", "--vers"])

    with pytest.raises(PoetryException) as cm:
        conf.create_io(app, args)

    stacktrace_files = [str(stack_frame.path) for stack_frame in cm.traceback]
    stacktrace_files_without_the_test_file = stacktrace_files[1:]
    assert all(("poetry" in path for path in stacktrace_files_without_the_test_file))

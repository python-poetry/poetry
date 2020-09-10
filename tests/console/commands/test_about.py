import pytest


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("about")


def test_about(tester):
    tester.execute()
    expected = """\
Poetry - Package Management for Python

Poetry is a dependency manager tracking local dependencies of your projects and libraries.
See https://github.com/python-poetry/poetry for more information.
"""

    assert expected == tester.io.fetch_output()

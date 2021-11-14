import pytest


@pytest.fixture
def tester(command_tester_factory, poetry_with_source, add_multiple_sources):
    return command_tester_factory("source show", poetry=poetry_with_source)


def test_source_show_simple(tester):
    tester.execute("")

    expected = """\
name       : existing
url        : https://existing.com
default    : no
secondary  : no

name       : one
url        : https://one.com
default    : no
secondary  : no

name       : two
url        : https://two.com
default    : no
secondary  : no
""".splitlines()
    assert (
        list(map(lambda l: l.strip(), tester.io.fetch_output().strip().splitlines()))
        == expected
    )
    assert tester.status_code == 0


def test_source_show_one(tester, source_one):
    tester.execute(f"{source_one.name}")

    expected = """\
name       : one
url        : https://one.com
default    : no
secondary  : no
""".splitlines()
    assert (
        list(map(lambda l: l.strip(), tester.io.fetch_output().strip().splitlines()))
        == expected
    )
    assert tester.status_code == 0


def test_source_show_two(tester, source_one, source_two):
    tester.execute(f"{source_one.name} {source_two.name}")

    expected = """\
name       : one
url        : https://one.com
default    : no
secondary  : no

name       : two
url        : https://two.com
default    : no
secondary  : no
""".splitlines()
    assert (
        list(map(lambda l: l.strip(), tester.io.fetch_output().strip().splitlines()))
        == expected
    )
    assert tester.status_code == 0


def test_source_show_error(tester):
    tester.execute("error")
    assert tester.io.fetch_error().strip() == "No source found with name(s): error"
    assert tester.status_code == 1

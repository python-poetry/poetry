import pytest


@pytest.fixture
def tester(command_tester_factory, poetry_with_source, add_multiple_sources):
    return command_tester_factory("source remove", poetry=poetry_with_source)


def test_source_remove_simple(
    tester, poetry_with_source, source_existing, source_one, source_two
):
    tester.execute(f"{source_existing.name}")
    assert (
        tester.io.fetch_output().strip()
        == f"Removing source with name {source_existing.name}."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()
    assert sources == [source_one, source_two]

    assert tester.status_code == 0


def test_source_remove_error(tester):
    tester.execute("error")
    assert tester.io.fetch_error().strip() == "Source with name error was not found."
    assert tester.status_code == 1

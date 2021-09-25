import pytest


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("install")


def test_group_options_are_passed_to_the_installer(tester, mocker):
    """
    Group options are passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--with foo,bar --without baz --without bim --only bam")

    assert tester.command.installer._with_groups == ["foo", "bar"]
    assert tester.command.installer._without_groups == ["baz", "bim"]
    assert tester.command.installer._only_groups == ["bam"]


def test_sync_option_is_passed_to_the_installer(tester, mocker):
    """
    The --sync option is passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization

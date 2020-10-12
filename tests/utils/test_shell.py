import pytest

from poetry.utils.shell import Shell as _Shell


@pytest.fixture
def Shell():
    _Shell._shell = None
    return _Shell


def test_name_and_path_properties(Shell):
    """
    Given a Shell object,
    Check that the name and path propterites
        match the _name and _path attributes,
        as well as the values passed in.
    """
    s = Shell(name="name", path="path")
    assert s.name == s._name == "name"
    assert s.path == s._path == "path"


def test_default_shell_is_None(Shell):
    """
    Given the Shell class,
    Check that _shell is None
    """
    assert Shell._shell is None


def test_get_when__shell_is_not_none(Shell):
    """
    Given the Shell class, when _shell is not None,
    Check that the get class method returns Shell._shell
    """
    s = Shell(name="name", path="path")
    Shell._shell = s
    assert Shell.get() == s


def test_get_when_detect_shell_works(Shell, mocker):
    """
    Given the Shell class,
    When Shell.get() is called, and shellingham.detect_shell()
        doesn't error.
    Check that the resulting shell's name and path are as expected,
        and that Shell._shell is updated.
    """
    mocker.patch(
        "poetry.utils.shell.detect_shell", return_value=("Mocked Name", "Mocked Path")
    )
    s = Shell.get()
    assert s.name == "Mocked Name"
    assert s.path == "Mocked Path"
    assert Shell._shell == s


def test_get_when_detect_shell_raises_error(Shell, mocker):
    """
    Given the Shell Class running on a posix system.
    When Shell.get() is called, and shellingham.detect_shell()
        raises an error, but os.environ.get is not None.
    Check that the resulting shell is as expected.
    """
    mocker.patch("poetry.utils.shell.detect_shell", side_effect=RuntimeError)
    mocker.patch(
        "poetry.utils.shell.os.environ.get", return_value="/blah/blah/blah/name"
    )

    s = Shell.get()
    assert s.name == "name"
    assert s.path == "/blah/blah/blah/name"
    assert Shell._shell == s


def test_get_when_detect_shell_raises_error_and_os_environ_get_returns_None(
    Shell, mocker
):
    """
    Given the Shell Class.
    When Shell.get() is called, shellingham.detect_shell() raises
        an error, and os.environ.get returns None (i.e. SHELL or
        COMSPEC environment variable isn't set).
    Check that RuntimeError is raised.
    """
    mocker.patch("poetry.utils.shell.detect_shell", side_effect=RuntimeError)
    mocker.patch("poetry.utils.shell.os.environ.get", return_value=None)

    excinfo = pytest.raises(RuntimeError, Shell.get)
    assert "Unable to detect the current shell." in str(excinfo)


@pytest.mark.parametrize(
    "s_name,suffix",
    [
        pytest.param("fish", ".fish", id="fish"),
        pytest.param("csh", ".csh", id="csh"),
        pytest.param("tcsh", ".csh", id="tcsh"),
        pytest.param("Anything Else", "", id="Default Case"),
    ],
)
def test__get_activate_script(s_name, suffix, Shell):
    """
    Given a Shell,
    Check that s._get_activate_script() returns the correct script.
    """
    s = Shell(name=s_name, path="path")
    assert s._get_activate_script() == "activate" + suffix


@pytest.mark.parametrize(
    "s_name,command",
    [
        pytest.param("fish", "source", id="fish"),
        pytest.param("csh", "source", id="csh"),
        pytest.param("tcsh", "source", id="tcsh"),
        pytest.param("Anything Else", ".", id="Default Case"),
    ],
)
def test__get_source_command(s_name, command, Shell):
    """
    Given a Shell,
    Check that s._get_source_command returns the correct command.
    """
    s = Shell(name=s_name, path="path")
    assert s._get_source_command() == command


def test___repr__(Shell):
    s = Shell(name="NAME", path="PATH")
    assert repr(s) == 'Shell("NAME", "PATH")'

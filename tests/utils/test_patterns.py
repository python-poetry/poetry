import pytest

from poetry.utils import patterns


@pytest.mark.parametrize(
    ["filename", "namever", "name", "ver", "build", "pyver", "abi", "plat"],
    [
        (
            "markdown_captions-2-py3-none-any.whl",
            "markdown_captions-2",
            "markdown_captions",
            "2",
            None,
            "py3",
            "none",
            "any",
        ),
        (
            "SQLAlchemy-1.3.20-cp27-cp27mu-manylinux2010_x86_64.whl",
            "SQLAlchemy-1.3.20",
            "SQLAlchemy",
            "1.3.20",
            None,
            "cp27",
            "cp27mu",
            "manylinux2010_x86_64",
        ),
    ],
)
def test_wheel_file_re(filename, namever, name, ver, build, pyver, abi, plat):
    match = patterns.wheel_file_re.match(filename)
    groups = match.groupdict()

    assert groups["namever"] == namever
    assert groups["name"] == name
    assert groups["ver"] == ver
    assert groups["build"] == build
    assert groups["pyver"] == pyver
    assert groups["abi"] == abi
    assert groups["plat"] == plat

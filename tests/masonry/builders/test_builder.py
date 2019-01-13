from poetry.io import NullIO
from poetry.masonry.builders.builder import Builder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv


def test_builder_find_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Poetry.create(Path(__file__).parent / "fixtures" / "complete"),
        NullEnv(),
        NullIO(),
    )

    assert builder.find_excluded_files() == {"my_package/sub_pkg1/extra_file.xml"}


def test_builder_find_case_sensitive_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Poetry.create(Path(__file__).parent / "fixtures" / "case_sensitive_exclusions"),
        NullEnv(),
        NullIO(),
    )

    assert builder.find_excluded_files() == {
        "my_package/FooBar/Bar.py",
        "my_package/FooBar/lowercasebar.py",
        "my_package/Foo/SecondBar.py",
        "my_package/Foo/Bar.py",
        "my_package/Foo/lowercasebar.py",
        "my_package/bar/foo.py",
        "my_package/bar/CapitalFoo.py",
    }


def test_builder_find_invalid_case_sensitive_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Poetry.create(
            Path(__file__).parent / "fixtures" / "invalid_case_sensitive_exclusions"
        ),
        NullEnv(),
        NullIO(),
    )

    assert {"my_package/Bar/foo/bar/Foo.py"} == builder.find_excluded_files()

# -*- coding: utf-8 -*-
from email.parser import Parser

from clikit.io import NullIO

from poetry.factory import Factory
from poetry.masonry.builders.builder import Builder
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv


def test_builder_find_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Factory().create_poetry(Path(__file__).parent / "fixtures" / "complete"),
        NullEnv(),
        NullIO(),
    )

    assert builder.find_excluded_files() == {"my_package/sub_pkg1/extra_file.xml"}


def test_builder_find_case_sensitive_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Factory().create_poetry(
            Path(__file__).parent / "fixtures" / "case_sensitive_exclusions"
        ),
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
        Factory().create_poetry(
            Path(__file__).parent / "fixtures" / "invalid_case_sensitive_exclusions"
        ),
        NullEnv(),
        NullIO(),
    )

    assert {"my_package/Bar/foo/bar/Foo.py"} == builder.find_excluded_files()


def test_get_metadata_content():
    builder = Builder(
        Factory().create_poetry(Path(__file__).parent / "fixtures" / "complete"),
        NullEnv(),
        NullIO(),
    )

    metadata = builder.get_metadata_content()

    p = Parser()
    parsed = p.parsestr(metadata)

    assert parsed["Metadata-Version"] == "2.1"
    assert parsed["Name"] == "my-package"
    assert parsed["Version"] == "1.2.3"
    assert parsed["Summary"] == "Some description."
    assert parsed["Author"] == "Sébastien Eustace"
    assert parsed["Author-email"] == "sebastien@eustace.io"
    assert parsed["Keywords"] == "packaging,dependency,poetry"
    assert parsed["Requires-Python"] == ">=3.6,<4.0"
    assert parsed["License"] == "MIT"
    assert parsed["Home-page"] == "https://poetry.eustace.io/"

    classifiers = parsed.get_all("Classifier")
    assert classifiers == [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]

    extras = parsed.get_all("Provides-Extra")
    assert extras == ["time"]

    requires = parsed.get_all("Requires-Dist")
    assert requires == [
        "cachy[msgpack] (>=0.2.0,<0.3.0)",
        "cleo (>=0.6,<0.7)",
        'pendulum (>=1.4,<2.0); (python_version ~= "2.7" and sys_platform == "win32" or python_version in "3.4 3.5") and (extra == "time")',
    ]

    urls = parsed.get_all("Project-URL")
    assert urls == [
        "Documentation, https://poetry.eustace.io/docs",
        "Issue Tracker, https://github.com/sdispater/poetry/issues",
        "Repository, https://github.com/sdispater/poetry",
    ]


def test_metadata_homepage_default():
    builder = Builder(
        Factory().create_poetry(Path(__file__).parent / "fixtures" / "simple_version"),
        NullEnv(),
        NullIO(),
    )

    metadata = Parser().parsestr(builder.get_metadata_content())

    assert metadata["Home-page"] is None


def test_metadata_with_vcs_dependencies():
    builder = Builder(
        Factory().create_poetry(
            Path(__file__).parent / "fixtures" / "with_vcs_dependency"
        ),
        NullEnv(),
        NullIO(),
    )

    metadata = Parser().parsestr(builder.get_metadata_content())

    requires_dist = metadata["Requires-Dist"]

    assert "cleo @ git+https://github.com/sdispater/cleo.git@master" == requires_dist


def test_metadata_with_url_dependencies():
    builder = Builder(
        Factory().create_poetry(
            Path(__file__).parent / "fixtures" / "with_url_dependency"
        ),
        NullEnv(),
        NullIO(),
    )

    metadata = Parser().parsestr(builder.get_metadata_content())

    requires_dist = metadata["Requires-Dist"]

    assert (
        "demo @ https://poetry.eustace.io/distributions/demo-0.1.0-py2.py3-none-any.whl"
        == requires_dist
    )

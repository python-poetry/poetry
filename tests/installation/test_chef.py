from packaging.tags import Tag
from poetry.core.packages.utils.link import Link
from poetry.installation.chef import Chef
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv


def test_get_cached_archive_for_link(config, mocker):
    chef = Chef(
        config,
        MockEnv(
            version_info=(3, 8, 3),
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"},
            supported_tags=[
                Tag("cp38", "cp38", "macosx_10_15_x86_64"),
                Tag("py3", "none", "any"),
            ],
        ),
    )

    mocker.patch.object(
        chef,
        "get_cached_archives_for_link",
        return_value=[
            Link("file:///foo/demo-0.1.0-py2.py3-none-any"),
            Link("file:///foo/demo-0.1.0.tar.gz"),
            Link("file:///foo/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl"),
            Link("file:///foo/demo-0.1.0-cp37-cp37-macosx_10_15_x86_64.whl"),
        ],
    )

    archive = chef.get_cached_archive_for_link(
        Link("https://files.python-poetry.org/demo-0.1.0.tar.gz")
    )

    assert Link("file:///foo/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl") == archive


def test_get_cached_archives_for_link(config, mocker):
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
    )

    mocker.patch.object(
        chef,
        "get_cache_directory_for_link",
        return_value=Path(__file__).parent.parent.joinpath("fixtures/distributions"),
    )

    archives = chef.get_cached_archives_for_link(
        Link("https://files.python-poetry.org/demo-0.1.0.tar.gz")
    )

    assert 2 == len(archives)


def test_get_cache_directory_for_link(config):
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
    )

    directory = chef.get_cache_directory_for_link(
        Link("https://files.python-poetry.org/poetry-1.1.0.tar.gz")
    )
    expected = Path(
        "/foo/artifacts/ba/63/13/283a3b3b7f95f05e9e6f84182d276f7bb0951d5b0cc24422b33f7a4648"
    )

    assert expected == directory


def test_no_backslashes_with_file_protocol(config, mocker):
    """Protocol file:// cannot be combined w/ backslashes on Windows."""
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
    )

    link = "https://files.pythonhosted.org/packages/96/0a/67556e9b7782df7118c1f49bdc494da5e5e429c93aa77965f33e81287c8c/zipp-1.2.0-py2.py3-none-any.whl#sha256=e0d9e63797e483a30d27e09fffd308c59a700d365ec34e93cc100844168bf921"
    mocked_cache_dir = Path("C:\\Users\\johnsmith\\AppData\\Local\\pypoetry\\Cache\\artifacts\\96\\15\\17\\6dc4596b5827e94647f1e4e7362bec368fcdda2100141109ada8a1e3dd")
    archive = Path("C:\\Users\\johnsmith\\AppData\\Local\\pypoetry\\Cache\\artifacts\\96\\15\\17\\6dc4596b5827e94647f1e4e7362bec368fcdda2100141109ada8a1e3dd\\zipp-1.2.0-py2.py3-none-any.whl")
    expected = "file://" + str(archive.as_posix())


    mocker.patch.object(
        chef,
        "get_cache_directory_for_link",
        return_value=mocked_cache_dir,
    )

    mocker.patch.object(
        Path,
        "glob",
        return_value=[archive],
    )

    archives = chef.get_cached_archives_for_link(link)

    assert str(archives[0]) == expected


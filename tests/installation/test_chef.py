from pathlib import Path

from packaging.tags import Tag

from poetry.core.packages.utils.link import Link
from poetry.installation.chef import Chef
from poetry.utils.env import EnvManager
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

    distributions = Path(__file__).parent.parent.joinpath("fixtures/distributions")
    mocker.patch.object(
        chef,
        "get_cache_directory_for_link",
        return_value=distributions,
    )

    archives = chef.get_cached_archives_for_link(
        Link("https://files.python-poetry.org/demo-0.1.0.tar.gz")
    )

    assert archives
    assert set(archives) == {
        Link(path.as_uri()) for path in distributions.glob("demo-0.1.*")
    }


def test_get_cache_directory_for_link(config, config_cache_dir):
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
        "{}/artifacts/ba/63/13/283a3b3b7f95f05e9e6f84182d276f7bb0951d5b0cc24422b33f7a4648".format(
            config_cache_dir.as_posix()
        )
    )

    assert expected == directory


def test_prepare_sdist(config, config_cache_dir):
    chef = Chef(config, EnvManager.get_system_env())

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/distributions/demo-0.1.0.tar.gz")
        .resolve()
    )

    destination = chef.get_cache_directory_for_link(Link(archive.as_uri()))

    wheel = chef.prepare(archive)

    assert wheel.parent == destination
    assert wheel.name == "demo-0.1.0-py3-none-any.whl"


def test_prepare_directory(config, config_cache_dir):
    chef = Chef(config, EnvManager.get_system_env())

    archive = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"


def test_prepare_directory_with_extensions(config, config_cache_dir):
    env = EnvManager.get_system_env()
    chef = Chef(config, env)

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve()
    )

    wheel = chef.prepare(archive)

    assert wheel.name == "extended-0.1-{}.whl".format(env.supported_tags[0])

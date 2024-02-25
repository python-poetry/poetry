from __future__ import annotations

from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.io.null_io import NullIO
from packaging.utils import canonicalize_name
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.directory_dependency import DirectoryDependency
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.url_dependency import URLDependency
from poetry.core.packages.vcs_dependency import VCSDependency

from poetry.factory import Factory
from poetry.inspection.info import PackageInfo
from poetry.packages import DependencyPackage
from poetry.puzzle.provider import IncompatibleConstraintsError
from poetry.puzzle.provider import Provider
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.repository import Repository
from poetry.repositories.repository_pool import Priority
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.helpers import get_dependency


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


SOME_URL = "https://example.com/path.tar.gz"


class MockEnv(BaseMockEnv):
    def run(self, bin: str, *args: str, **kwargs: Any) -> str:
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


@pytest.fixture
def root() -> ProjectPackage:
    return ProjectPackage("root", "1.2.3")


@pytest.fixture
def repository() -> Repository:
    return Repository("repo")


@pytest.fixture
def pool(repository: Repository) -> RepositoryPool:
    pool = RepositoryPool()
    pool.add_repository(repository)

    return pool


@pytest.fixture
def provider(root: ProjectPackage, pool: RepositoryPool) -> Provider:
    return Provider(root, pool, NullIO())


@pytest.mark.parametrize(
    "dependency, expected",
    [
        (Dependency("foo", "<2"), [Package("foo", "1")]),
        (Dependency("foo", "<2", extras=["bar"]), [Package("foo", "1")]),
        (Dependency("foo", ">=1"), [Package("foo", "2"), Package("foo", "1")]),
        (Dependency("foo", ">=1a"), [Package("foo", "2"), Package("foo", "1")]),
        (
            Dependency("foo", ">=1", allows_prereleases=True),
            [
                Package("foo", "3a"),
                Package("foo", "2"),
                Package("foo", "2a"),
                Package("foo", "1"),
            ],
        ),
    ],
)
def test_search_for(
    provider: Provider,
    repository: Repository,
    dependency: Dependency,
    expected: list[Package],
) -> None:
    foo1 = Package("foo", "1")
    foo2a = Package("foo", "2a")
    foo2 = Package("foo", "2")
    foo3a = Package("foo", "3a")
    repository.add_package(foo1)
    repository.add_package(foo2a)
    repository.add_package(foo2)
    repository.add_package(foo3a)

    assert provider.search_for(dependency) == expected


@pytest.mark.parametrize(
    "dependency, direct_origin_dependency, expected_before, expected_after",
    [
        (
            Dependency("foo", ">=1"),
            URLDependency("foo", SOME_URL),
            [Package("foo", "3")],
            [Package("foo", "2a", source_type="url", source_url=SOME_URL)],
        ),
        (
            Dependency("foo", ">=2"),
            URLDependency("foo", SOME_URL),
            [Package("foo", "3")],
            [Package("foo", "3")],
        ),
        (
            Dependency("foo", ">=1", extras=["bar"]),
            URLDependency("foo", SOME_URL),
            [Package("foo", "3")],
            [Package("foo", "2a", source_type="url", source_url=SOME_URL)],
        ),
        (
            Dependency("foo", ">=1"),
            URLDependency("foo", SOME_URL, extras=["baz"]),
            [Package("foo", "3")],
            [Package("foo", "2a", source_type="url", source_url=SOME_URL)],
        ),
        (
            Dependency("foo", ">=1", extras=["bar"]),
            URLDependency("foo", SOME_URL, extras=["baz"]),
            [Package("foo", "3")],
            [Package("foo", "2a", source_type="url", source_url=SOME_URL)],
        ),
    ],
)
def test_search_for_direct_origin_and_extras(
    provider: Provider,
    repository: Repository,
    mocker: MockerFixture,
    dependency: Dependency,
    direct_origin_dependency: Dependency,
    expected_before: list[Package],
    expected_after: list[Package],
) -> None:
    foo2a_direct_origin = Package("foo", "2a", source_type="url", source_url=SOME_URL)
    mocker.patch(
        "poetry.puzzle.provider.Provider.search_for_direct_origin_dependency",
        return_value=foo2a_direct_origin,
    )
    foo2a = Package("foo", "2a")
    foo3 = Package("foo", "3")
    repository.add_package(foo2a)
    repository.add_package(foo3)

    assert provider.search_for(dependency) == expected_before
    assert provider.search_for(direct_origin_dependency) == [foo2a_direct_origin]
    assert provider.search_for(dependency) == expected_after


@pytest.mark.parametrize("value", [True, False])
def test_search_for_vcs_retains_develop_flag(provider: Provider, value: bool) -> None:
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", develop=value
    )
    package = provider.search_for_direct_origin_dependency(dependency)
    assert package.develop == value


def test_search_for_vcs_setup_egg_info(provider: Provider) -> None:
    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_setup_egg_info_with_extras(provider: Provider) -> None:
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_read_setup(provider: Provider, mocker: MockerFixture) -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_read_setup_with_extras(
    provider: Provider, mocker: MockerFixture
) -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]


def test_search_for_vcs_read_setup_raises_error_if_no_version(
    provider: Provider, mocker: MockerFixture
) -> None:
    mocker.patch(
        "poetry.inspection.info.get_pep517_metadata",
        return_value=PackageInfo(name="demo", version=None),
    )

    dependency = VCSDependency("demo", "git", "https://github.com/demo/no-version.git")

    with pytest.raises(RuntimeError):
        provider.search_for_direct_origin_dependency(dependency)


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
def test_search_for_directory_setup_egg_info(
    provider: Provider, directory: str, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / directory,
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_egg_info_with_extras(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / "demo",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
def test_search_for_directory_setup_with_base(
    provider: Provider, directory: str, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / directory,
        base=fixture_dir("git") / "github.com" / "demo" / directory,
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }
    assert package.root_dir == (fixture_dir("git") / "github.com" / "demo" / directory)


def test_search_for_directory_setup_read_setup(
    provider: Provider, mocker: MockerFixture, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / "demo",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_read_setup_with_extras(
    provider: Provider, mocker: MockerFixture, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / "demo",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_read_setup_with_no_dependencies(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "demo",
        fixture_dir("git") / "github.com" / "demo" / "no-dependencies",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"
    assert package.requires == []
    assert package.extras == {}


def test_search_for_directory_poetry(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "project-with-extras",
        fixture_dir("project_with_extras"),
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "project-with-extras"
    assert package.version.text == "1.2.3"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == []
    assert optional == [
        get_dependency("cachy", ">=0.2.0"),
        get_dependency("pendulum", ">=1.4.4"),
    ]
    extras_a = canonicalize_name("extras-a")
    extras_b = canonicalize_name("extras-b")
    assert set(package.extras) == {extras_a, extras_b}
    assert set(package.extras[extras_a]) == {get_dependency("pendulum", ">=1.4.4")}
    assert set(package.extras[extras_b]) == {get_dependency("cachy", ">=0.2.0")}


def test_search_for_directory_poetry_with_extras(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = DirectoryDependency(
        "project-with-extras",
        fixture_dir("project_with_extras"),
        extras=["extras_a"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "project-with-extras"
    assert package.version.text == "1.2.3"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == []
    assert optional == [
        get_dependency("cachy", ">=0.2.0"),
        get_dependency("pendulum", ">=1.4.4"),
    ]
    extras_a = canonicalize_name("extras-a")
    extras_b = canonicalize_name("extras-b")
    assert set(package.extras) == {extras_a, extras_b}
    assert set(package.extras[extras_a]) == {get_dependency("pendulum", ">=1.4.4")}
    assert set(package.extras[extras_b]) == {get_dependency("cachy", ">=0.2.0")}


def test_search_for_file_sdist(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = FileDependency(
        "demo",
        fixture_dir("distributions") / "demo-0.1.0.tar.gz",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_sdist_with_extras(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = FileDependency(
        "demo",
        fixture_dir("distributions") / "demo-0.1.0.tar.gz",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_wheel(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = FileDependency(
        "demo",
        fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_wheel_with_extras(
    provider: Provider, fixture_dir: FixtureDirGetter
) -> None:
    dependency = FileDependency(
        "demo",
        fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_complete_package_merges_same_source_and_no_source(
    provider: Provider, root: ProjectPackage
) -> None:
    foo_no_source_1 = get_dependency("foo", ">=1")
    foo_source_1 = get_dependency("foo", "!=1.1.*")
    foo_source_1.source_name = "source"
    foo_source_2 = get_dependency("foo", "!=1.2.*")
    foo_source_2.source_name = "source"
    foo_no_source_2 = get_dependency("foo", "<2")

    root.add_dependency(foo_no_source_1)
    root.add_dependency(foo_source_1)
    root.add_dependency(foo_source_2)
    root.add_dependency(foo_no_source_2)

    complete_package = provider.complete_package(
        DependencyPackage(root.to_dependency(), root)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 1
    assert requires[0].source_name == "source"
    assert str(requires[0].constraint) in {
        ">=1,<1.1 || >=1.3,<2",
        ">=1,<1.1.dev0 || >=1.3.dev0,<2",
        ">=1,<1.1.0 || >=1.3.0,<2",
        ">=1,<1.1.0.dev0 || >=1.3.0.dev0,<2",
    }


def test_complete_package_does_not_merge_different_source_names(
    provider: Provider, root: ProjectPackage
) -> None:
    foo_source_1 = get_dependency("foo")
    foo_source_1.source_name = "source_1"
    foo_source_2 = get_dependency("foo")
    foo_source_2.source_name = "source_2"

    root.add_dependency(foo_source_1)
    root.add_dependency(foo_source_2)

    with pytest.raises(IncompatibleConstraintsError) as e:
        provider.complete_package(DependencyPackage(root.to_dependency(), root))

    expected = """\
Incompatible constraints in requirements of root (1.2.3):
foo ; source=source_2
foo ; source=source_1"""

    assert str(e.value) == expected


def test_complete_package_merges_same_source_type_and_no_source(
    provider: Provider, root: ProjectPackage, fixture_dir: FixtureDirGetter
) -> None:
    project_dir = fixture_dir("with_conditional_path_deps")
    path = (project_dir / "demo_one").as_posix()

    root.add_dependency(Factory.create_dependency("demo", ">=1.0"))
    root.add_dependency(Factory.create_dependency("demo", {"path": path}))
    root.add_dependency(Factory.create_dependency("demo", {"path": path}))  # duplicate
    root.add_dependency(Factory.create_dependency("demo", "<2.0"))

    complete_package = provider.complete_package(
        DependencyPackage(root.to_dependency(), root)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 1
    assert requires[0].source_url == path
    assert str(requires[0].constraint) == "1.2.3"


def test_complete_package_does_not_merge_different_source_types(
    provider: Provider, root: ProjectPackage, fixture_dir: FixtureDirGetter
) -> None:
    project_dir = fixture_dir("with_conditional_path_deps")
    for folder in ["demo_one", "demo_two"]:
        path = (project_dir / folder).as_posix()
        root.add_dependency(Factory.create_dependency("demo", {"path": path}))

    with pytest.raises(IncompatibleConstraintsError) as e:
        provider.complete_package(DependencyPackage(root.to_dependency(), root))

    expected = f"""\
Incompatible constraints in requirements of root (1.2.3):
demo @ {project_dir.as_uri()}/demo_two (1.2.3)
demo @ {project_dir.as_uri()}/demo_one (1.2.3)"""

    assert str(e.value) == expected


def test_complete_package_does_not_merge_different_source_type_and_name(
    provider: Provider, root: ProjectPackage, fixture_dir: FixtureDirGetter
) -> None:
    project_dir = fixture_dir("with_conditional_path_deps")
    path = (project_dir / "demo_one").as_posix()

    dep_with_source_name = Factory.create_dependency("demo", ">=1.0")
    dep_with_source_name.source_name = "source"
    root.add_dependency(dep_with_source_name)
    root.add_dependency(Factory.create_dependency("demo", {"path": path}))

    with pytest.raises(IncompatibleConstraintsError) as e:
        provider.complete_package(DependencyPackage(root.to_dependency(), root))

    expected = f"""\
Incompatible constraints in requirements of root (1.2.3):
demo @ {project_dir.as_uri()}/demo_one (1.2.3)
demo (>=1.0) ; source=source"""

    assert str(e.value) == expected


def test_complete_package_does_not_merge_different_subdirectories(
    provider: Provider, root: ProjectPackage
) -> None:
    dependency_one = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one",
        },
    )
    dependency_one_copy = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one-copy",
        },
    )

    root.add_dependency(dependency_one)
    root.add_dependency(dependency_one_copy)

    with pytest.raises(IncompatibleConstraintsError) as e:
        provider.complete_package(DependencyPackage(root.to_dependency(), root))

    expected = """\
Incompatible constraints in requirements of root (1.2.3):
one @ git+https://github.com/demo/subdirectories.git#subdirectory=one-copy (1.0.0)
one @ git+https://github.com/demo/subdirectories.git#subdirectory=one (1.0.0)"""

    assert str(e.value) == expected


@pytest.mark.parametrize("source_name", [None, "repo"])
def test_complete_package_with_extras_preserves_source_name(
    provider: Provider, repository: Repository, source_name: str | None
) -> None:
    package_a = Package("A", "1.0")
    package_b = Package("B", "1.0")
    dep = get_dependency("B", "^1.0", optional=True)
    package_a.add_dependency(dep)
    package_a.extras = {canonicalize_name("foo"): [dep]}
    repository.add_package(package_a)
    repository.add_package(package_b)

    dependency = Dependency("A", "1.0", extras=["foo"])
    if source_name:
        dependency.source_name = source_name

    complete_package = provider.complete_package(
        DependencyPackage(dependency, package_a)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 2
    assert requires[0].name == "a"
    assert requires[0].source_name == source_name
    assert requires[1].name == "b"
    assert requires[1].source_name is None


@pytest.mark.parametrize("with_extra", [False, True])
def test_complete_package_fetches_optional_vcs_dependency_only_if_requested(
    provider: Provider, repository: Repository, mocker: MockerFixture, with_extra: bool
) -> None:
    optional_vcs_dependency = Factory.create_dependency(
        "demo", {"git": "https://github.com/demo/demo.git", "optional": True}
    )
    package = Package("A", "1.0", features=["foo"] if with_extra else [])
    package.add_dependency(optional_vcs_dependency)
    package.extras = {canonicalize_name("foo"): [optional_vcs_dependency]}
    repository.add_package(package)

    spy = mocker.spy(provider, "_search_for_vcs")

    provider.complete_package(DependencyPackage(package.to_dependency(), package))

    if with_extra:
        spy.assert_called()
    else:
        spy.assert_not_called()


def test_complete_package_finds_locked_package_in_explicit_source(
    root: ProjectPackage, pool: RepositoryPool
) -> None:
    package = Package("a", "1.0", source_reference="explicit")
    explicit_repo = Repository("explicit")
    explicit_repo.add_package(package)
    pool.add_repository(explicit_repo, priority=Priority.EXPLICIT)

    root_dependency = get_dependency("a", ">0")
    root_dependency.source_name = "explicit"
    root.add_dependency(root_dependency)
    locked_package = Package("a", "1.0", source_reference="explicit")
    provider = Provider(root, pool, NullIO(), locked=[locked_package])
    provider.complete_package(DependencyPackage(root.to_dependency(), root))

    # transitive dependency without explicit source
    dependency = get_dependency("a", ">=1")

    locked = provider.get_locked(dependency)
    assert locked is not None
    provider.complete_package(locked)  # must not fail


def test_complete_package_finds_locked_package_in_other_source(
    root: ProjectPackage, repository: Repository, pool: RepositoryPool
) -> None:
    package = Package("a", "1.0")
    repository.add_package(package)
    explicit_repo = Repository("explicit")
    pool.add_repository(explicit_repo)

    root_dependency = get_dependency("a", ">0")  # no explicit source
    root.add_dependency(root_dependency)
    locked_package = Package("a", "1.0", source_reference="explicit")  # explicit source
    provider = Provider(root, pool, NullIO(), locked=[locked_package])
    provider.complete_package(DependencyPackage(root.to_dependency(), root))

    # transitive dependency without explicit source
    dependency = get_dependency("a", ">=1")

    locked = provider.get_locked(dependency)
    assert locked is not None
    provider.complete_package(locked)  # must not fail


def test_complete_package_raises_packagenotfound_if_locked_source_not_available(
    root: ProjectPackage, pool: RepositoryPool, provider: Provider
) -> None:
    locked_package = Package("a", "1.0", source_reference="outdated")
    provider = Provider(root, pool, NullIO(), locked=[locked_package])
    provider.complete_package(DependencyPackage(root.to_dependency(), root))

    # transitive dependency without explicit source
    dependency = get_dependency("a", ">=1")

    locked = provider.get_locked(dependency)
    assert locked is not None
    with pytest.raises(PackageNotFound):
        provider.complete_package(locked)


def test_source_dependency_is_satisfied_by_direct_origin(
    provider: Provider, repository: Repository
) -> None:
    direct_origin_package = Package("foo", "1.1", source_type="url")
    repository.add_package(Package("foo", "1.0"))
    provider._direct_origin_packages = {"foo": direct_origin_package}
    dep = Dependency("foo", ">=1")

    assert provider.search_for(dep) == [direct_origin_package]


def test_explicit_source_dependency_is_not_satisfied_by_direct_origin(
    provider: Provider, repository: Repository
) -> None:
    repo_package = Package("foo", "1.0")
    repository.add_package(repo_package)
    provider._direct_origin_packages = {"foo": Package("foo", "1.1", source_type="url")}
    dep = Dependency("foo", ">=1")
    dep.source_name = repository.name

    assert provider.search_for(dep) == [repo_package]


def test_source_dependency_is_not_satisfied_by_incompatible_direct_origin(
    provider: Provider, repository: Repository
) -> None:
    repo_package = Package("foo", "2.0")
    repository.add_package(repo_package)
    provider._direct_origin_packages = {"foo": Package("foo", "1.0", source_type="url")}
    dep = Dependency("foo", ">=2")
    dep.source_name = repository.name

    assert provider.search_for(dep) == [repo_package]

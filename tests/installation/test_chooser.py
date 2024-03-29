from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from packaging.tags import Tag
from poetry.core.packages.package import Package

from poetry.installation.chooser import Chooser
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from tests.conftest import Config
    from tests.types import DistributionHashGetter
    from tests.types import SpecializedLegacyRepositoryMocker

JSON_FIXTURES = (
    Path(__file__).parent.parent / "repositories" / "fixtures" / "pypi.org" / "json"
)

LEGACY_FIXTURES = Path(__file__).parent.parent / "repositories" / "fixtures" / "legacy"


@pytest.fixture()
def env() -> MockEnv:
    return MockEnv(
        supported_tags=[
            Tag("cp37", "cp37", "macosx_10_15_x86_64"),
            Tag("py3", "none", "any"),
        ]
    )


@pytest.fixture()
def pool(legacy_repository: LegacyRepository) -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(PyPiRepository(disable_cache=True))
    pool.add_repository(
        LegacyRepository("foo", "https://legacy.foo.bar/simple/", disable_cache=True)
    )
    pool.add_repository(
        LegacyRepository("foo2", "https://legacy.foo2.bar/simple/", disable_cache=True)
    )
    return pool


def check_chosen_link_filename(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    filename: str | None,
    config: Config | None = None,
    package_name: str = "pytest",
    package_version: str = "3.5.0",
) -> None:
    chooser = Chooser(pool, env, config)
    package = Package(package_name, package_version)

    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://legacy.foo.bar/simple/",
        )

    try:
        link = chooser.choose_for(package)
    except RuntimeError as e:
        if filename is None:
            assert (
                str(e)
                == f"Unable to find installation candidates for {package.name} ({package.version})"
            )
        else:
            pytest.fail("Package was not found")
    else:
        assert link.filename == filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_universal_wheel_link_if_available(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    check_chosen_link_filename(
        env, source_type, pool, "pytest-3.5.0-py2.py3-none-any.whl"
    )


@pytest.mark.parametrize(
    ("policy", "filename"),
    [
        (":all:", "pytest-3.5.0.tar.gz"),
        (":none:", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("black", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("pytest", "pytest-3.5.0.tar.gz"),
        ("pytest,black", "pytest-3.5.0.tar.gz"),
    ],
)
@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_no_binary_policy(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    policy: str,
    filename: str,
    config: Config,
) -> None:
    config.merge({"installer": {"no-binary": policy.split(",")}})
    check_chosen_link_filename(env, source_type, pool, filename, config)


@pytest.mark.parametrize(
    ("policy", "filename"),
    [
        (":all:", "pytest-3.5.0-py2.py3-none-any.whl"),
        (":none:", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("black", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("pytest", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("pytest,black", "pytest-3.5.0-py2.py3-none-any.whl"),
    ],
)
@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_only_binary_policy(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    policy: str,
    filename: str,
    config: Config,
) -> None:
    config.merge({"installer": {"only-binary": policy.split(",")}})
    check_chosen_link_filename(env, source_type, pool, filename, config)


@pytest.mark.parametrize(
    ("no_binary", "only_binary", "filename"),
    [
        (":all:", ":all:", None),
        (":none:", ":none:", "pytest-3.5.0-py2.py3-none-any.whl"),
        (":none:", ":all:", "pytest-3.5.0-py2.py3-none-any.whl"),
        (":all:", ":none:", "pytest-3.5.0.tar.gz"),
        ("black", "black", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("black", "pytest", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("pytest", "black", "pytest-3.5.0.tar.gz"),
        ("pytest", "pytest", None),
        ("pytest,black", "pytest,black", None),
    ],
)
@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_multiple_binary_policy(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    no_binary: str,
    only_binary: str,
    filename: str | None,
    config: Config,
) -> None:
    config.merge(
        {
            "installer": {
                "no-binary": no_binary.split(","),
                "only-binary": only_binary.split(","),
            }
        }
    )
    check_chosen_link_filename(env, source_type, pool, filename, config)


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_specific_python_universal_wheel_link_if_available(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    check_chosen_link_filename(
        env, source_type, pool, "isort-4.3.4-py3-none-any.whl", None, "isort", "4.3.4"
    )


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_system_specific_wheel_link_if_available(
    source_type: str, pool: RepositoryPool
) -> None:
    env = MockEnv(
        supported_tags=[Tag("cp37", "cp37m", "win32"), Tag("py3", "none", "any")]
    )
    check_chosen_link_filename(
        env,
        source_type,
        pool,
        "PyYAML-3.13-cp37-cp37m-win32.whl",
        None,
        "pyyaml",
        "3.13.0",
    )


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_sdist_if_no_compatible_wheel_link_is_available(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    check_chosen_link_filename(
        env, source_type, pool, "PyYAML-3.13.tar.gz", None, "pyyaml", "3.13.0"
    )


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_distributions_that_match_the_package_hashes(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    dist_hash_getter: DistributionHashGetter,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    files = [
        {
            "file": filename,
            "hash": (f"sha256:{dist_hash_getter(filename).sha256}"),
        }
        for filename in [
            f"{package.name}-{package.version}.tar.gz",
        ]
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://legacy.foo.bar/simple/",
        )

    package.files = files

    link = chooser.choose_for(package)

    assert link.filename == "isort-4.3.4.tar.gz"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_yanked_if_no_others(
    env: MockEnv,
    source_type: str,
    pool: RepositoryPool,
    dist_hash_getter: DistributionHashGetter,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("black", "21.11b0")
    files = [
        {
            "filename": filename,
            "hash": (f"sha256:{dist_hash_getter(filename).sha256}"),
        }
        for filename in [f"{package.name}-{package.version}-py3-none-any.whl"]
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://legacy.foo.bar/simple/",
        )

    package.files = files

    link = chooser.choose_for(package)

    assert link.filename == "black-21.11b0-py3-none-any.whl"
    assert link.yanked


def test_chooser_does_not_choose_yanked_if_others(
    specialized_legacy_repository_mocker: SpecializedLegacyRepositoryMocker,
    pool: RepositoryPool,
    dist_hash_getter: DistributionHashGetter,
) -> None:
    chooser = Chooser(pool, MockEnv(supported_tags=[Tag("py2", "none", "any")]))

    repo = pool.repository("foo2")
    pool.remove_repository("foo2")

    assert isinstance(repo, LegacyRepository)
    pool.add_repository(
        specialized_legacy_repository_mocker("-partial-yank", repo.name, repo.url)
    )

    package = Package("futures", "3.2.0")
    files = [
        {
            "filename": filename,
            "hash": (f"sha256:{dist_hash_getter(filename).sha256}"),
        }
        for filename in [
            f"{package.name}-{package.version}-py2-none-any.whl",
            f"{package.name}-{package.version}.tar.gz",
        ]
    ]
    package = Package(
        package.name,
        package.version.text,
        source_type="legacy",
        source_reference="foo",
        source_url="https://legacy.foo.bar/simple/",
    )
    package_partial_yank = Package(
        package.name,
        package.version.text,
        source_type="legacy",
        source_reference="foo2",
        source_url="https://legacy.foo2.bar/simple/",
    )

    package.files = files
    package_partial_yank.files = files

    link = chooser.choose_for(package)
    link_partial_yank = chooser.choose_for(package_partial_yank)

    assert link.filename == "futures-3.2.0-py2-none-any.whl"
    assert link_partial_yank.filename == "futures-3.2.0.tar.gz"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_throws_an_error_if_package_hashes_do_not_match(
    env: MockEnv,
    source_type: None,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    files = [
        {
            "hash": (
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            ),
            "filename": "isort-4.3.4.tar.gz",
        }
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://legacy.foo.bar/simple/",
        )

    package.files = files

    with pytest.raises(RuntimeError) as e:
        chooser.choose_for(package)
    assert files[0]["hash"] in str(e)


def test_chooser_md5_remote_fallback_to_sha256_inline_calculation(
    env: MockEnv, pool: RepositoryPool, dist_hash_getter: DistributionHashGetter
) -> None:
    chooser = Chooser(pool, env)
    package = Package(
        "demo",
        "0.1.0",
        source_type="legacy",
        source_reference="foo",
        source_url="https://legacy.foo.bar/simple/",
    )
    package.files = [
        {
            "filename": filename,
            "hash": (f"sha256:{dist_hash_getter(filename).sha256}"),
        }
        for filename in [f"{package.name}-{package.version}.tar.gz"]
    ]
    res = chooser.choose_for(package)
    assert res.filename == "demo-0.1.0.tar.gz"

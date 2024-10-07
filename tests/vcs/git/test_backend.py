from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dulwich.client import FetchPackResult
from dulwich.repo import Repo
from tests.helpers import MOCK_DEFAULT_GIT_REVISION

from poetry.packages.direct_origin import _get_package_from_git
from poetry.vcs.git.backend import Git
from poetry.vcs.git.backend import GitRefSpec
from poetry.vcs.git.backend import annotated_tag
from poetry.vcs.git.backend import is_revision_sha
from poetry.vcs.git.backend import urlpathjoin


VALID_SHA = "c5c7624ef64f34d9f50c3b7e8118f7f652fddbbd"


@pytest.fixture(autouse=True)
def git_mock() -> Repo:
    repo = MagicMock(spec=Repo)

    repo.get_config.return_value.get.return_value = (
        b"https://github.com/python-poetry/poetry.git"
    )

    repo.head.return_value = MOCK_DEFAULT_GIT_REVISION.encode("utf-8")

    # Clear any cache in the Git module
    _get_package_from_git.cache_clear()

    return repo


@pytest.fixture()
def fetch_pack_result() -> MagicMock:
    mock_fetch_pack_result = MagicMock(spec=FetchPackResult)
    mock_fetch_pack_result.refs = {
        b"refs/heads/main": b"abc123",
        b"refs/tags/v1.0.0": b"def456",
        annotated_tag(b"refs/tags/v1.0.0"): b"def456",
        b"HEAD": b"abc123",
    }
    mock_fetch_pack_result.symrefs = {b"HEAD": b"refs/heads/main"}

    return mock_fetch_pack_result


def test_invalid_revision_sha() -> None:
    result = is_revision_sha("invalid_input")
    assert result is False


def test_valid_revision_sha() -> None:
    result = is_revision_sha(VALID_SHA)
    assert result is True


def test_invalid_revision_sha_min_len() -> None:
    result = is_revision_sha("c5c7")
    assert result is False


def test_invalid_revision_sha_max_len() -> None:
    result = is_revision_sha(VALID_SHA + "42")
    assert result is False


@pytest.mark.parametrize(
    ("url"),
    [
        "git@github.com:python-poetry/poetry.git",
        "https://github.com/python-poetry/poetry.git",
        "https://github.com/python-poetry/poetry",
        "https://github.com/python-poetry/poetry/",
    ],
)
def test_get_name_from_source_url(url: str) -> None:
    name = Git.get_name_from_source_url(url)
    assert name == "poetry"


@pytest.mark.parametrize(("tag"), ["my-tag", b"my-tag"])
def test_annotated_tag(tag: str | bytes) -> None:
    tag = annotated_tag("my-tag")
    assert tag == b"my-tag^{}"


def test_get_remote_url(git_mock: Repo) -> None:
    repo = git_mock

    assert Git.get_remote_url(repo) == "https://github.com/python-poetry/poetry.git"


def test_get_revision(git_mock: Repo) -> None:
    assert Git.get_revision(git_mock) == MOCK_DEFAULT_GIT_REVISION


def test_info(git_mock: Repo) -> None:
    repo = git_mock
    info = Git.info(repo)

    assert info.origin == "https://github.com/python-poetry/poetry.git"
    assert (
        info.revision == MOCK_DEFAULT_GIT_REVISION
    )  # revision already mocked in helper


@pytest.mark.parametrize(
    "url, expected_result",
    [
        ("ssh://git@github.com/org/repo", "ssh://git@github.com/other-repo"),
        ("ssh://git@github.com/org/repo/", "ssh://git@github.com/org/other-repo"),
    ],
)
def test_urlpathjoin(url: str, expected_result: str) -> None:
    path = "../other-repo"
    result = urlpathjoin(url, path)
    assert result == expected_result


def test_git_refspec() -> None:
    git_ref = GitRefSpec("main", "1234", "v2")

    assert git_ref.branch == "main"
    assert git_ref.revision == "1234"
    assert git_ref.tag == "v2"
    assert git_ref.ref == b"HEAD"


@pytest.mark.parametrize(
    "refspec_params, expected_ref, expected_branch, expected_revision, expected_tag",
    [
        ({"branch": "main"}, b"refs/heads/main", "main", None, None),
        (
            {"revision": "v1.0.0"},
            annotated_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
        ({"revision": "abc"}, b"refs/heads/main", None, "abc", None),
    ],
)
def test_git_ref_spec_resolve(
    fetch_pack_result: FetchPackResult,
    refspec_params: dict[str, str | bytes | None],
    expected_ref: bytes,
    expected_branch: str,
    expected_revision: str,
    expected_tag: str,
) -> None:
    """
    Parameterized test for GitRefSpec resolve with different parameters.

    Args:
        fetch_pack_result (FetchPackResult): The mocked FetchPackResult object.
        refspec_params (dict): Parameters for creating GitRefSpec.
        expected_ref (bytes): The expected resolved ref.
        expected_branch (str): The expected resolved branch.
        expected_revision (str): The expected resolved revision.
        expected_tag (str): The expected resolved tag.
    """
    refspec = GitRefSpec(**refspec_params)
    refspec.resolve(fetch_pack_result)

    assert refspec.ref == expected_ref
    assert refspec.branch == expected_branch
    assert refspec.revision == expected_revision
    assert refspec.tag == expected_tag

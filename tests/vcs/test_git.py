import pytest

from poetry.vcs.git import Git
from poetry.vcs.git import GitUrl


@pytest.mark.parametrize(
    "url, normalized",
    [
        (
            "git+ssh://user@hostname:project.git#commit",
            GitUrl("user@hostname:project.git", "commit"),
        ),
        (
            "git+http://user@hostname/project/blah.git@commit",
            GitUrl("http://user@hostname/project/blah.git", "commit"),
        ),
        (
            "git+https://user@hostname/project/blah.git",
            GitUrl("https://user@hostname/project/blah.git", None),
        ),
        (
            "git+https://user@hostname:project/blah.git",
            GitUrl("https://user@hostname/project/blah.git", None),
        ),
        (
            "git+ssh://git@github.com:sdispater/poetry.git#v1.0.27",
            GitUrl("git@github.com:sdispater/poetry.git", "v1.0.27"),
        ),
        (
            "git+ssh://git@github.com:/sdispater/poetry.git",
            GitUrl("git@github.com:/sdispater/poetry.git", None),
        ),
        ("git+ssh://git@github.com:org/repo", GitUrl("git@github.com:org/repo", None),),
        (
            "git+ssh://git@github.com/org/repo",
            GitUrl("ssh://git@github.com/org/repo", None),
        ),
        ("git+ssh://foo:22/some/path", GitUrl("ssh://foo:22/some/path", None)),
        ("git@github.com:org/repo", GitUrl("git@github.com:org/repo", None)),
        (
            "git+https://github.com/sdispater/pendulum",
            GitUrl("https://github.com/sdispater/pendulum", None),
        ),
        (
            "git+https://github.com/sdispater/pendulum#7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
            GitUrl(
                "https://github.com/sdispater/pendulum",
                "7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
            ),
        ),
        (
            "git+ssh://git@git.example.com:b/b.git#v1.0.0",
            GitUrl("git@git.example.com:b/b.git", "v1.0.0"),
        ),
        (
            "git+ssh://git@github.com:sdispater/pendulum.git#foo/bar",
            GitUrl("git@github.com:sdispater/pendulum.git", "foo/bar"),
        ),
        ("git+file:///foo/bar.git", GitUrl("file:///foo/bar.git", None)),
        (
            "git+file://C:\\Users\\hello\\testing.git#zkat/windows-files",
            GitUrl("file://C:\\Users\\hello\\testing.git", "zkat/windows-files"),
        ),
    ],
)
def test_normalize_url(url, normalized):
    assert normalized == Git.normalize_url(url)

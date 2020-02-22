import pytest

from poetry.vcs.git import Git
from poetry.vcs.git import GitUrl
from poetry.vcs.git import ParsedUrl


@pytest.mark.parametrize(
    "url, normalized",
    [
        (
            "git+ssh://user@hostname:project.git#commit",
            GitUrl("user@hostname:project.git", "commit", None),
        ),
        (
            "git+http://user@hostname/project/blah.git@commit",
            GitUrl("http://user@hostname/project/blah.git", "commit", None),
        ),
        (
            "git+https://user@hostname/project/blah.git",
            GitUrl("https://user@hostname/project/blah.git", None, None),
        ),
        (
            "git+https://user@hostname/project~_-.foo/blah~_-.bar.git",
            GitUrl("https://user@hostname/project~_-.foo/blah~_-.bar.git", None, None),
        ),
        (
            "git+https://user@hostname:project/blah.git",
            GitUrl("https://user@hostname/project/blah.git", None, None),
        ),
        (
            "git+ssh://git@github.com:sdispater/poetry.git#v1.0.27",
            GitUrl("git@github.com:sdispater/poetry.git", "v1.0.27", None),
        ),
        (
            "git+ssh://git@github.com:/sdispater/poetry.git",
            GitUrl("git@github.com:/sdispater/poetry.git", None, None),
        ),
        (
            "git+ssh://git@github.com:org/repo",
            GitUrl("git@github.com:org/repo", None, None),
        ),
        (
            "git+ssh://git@github.com/org/repo",
            GitUrl("ssh://git@github.com/org/repo", None, None),
        ),
        ("git+ssh://foo:22/some/path", GitUrl("ssh://foo:22/some/path", None, None)),
        ("git@github.com:org/repo", GitUrl("git@github.com:org/repo", None, None)),
        (
            "git+https://github.com/sdispater/pendulum",
            GitUrl("https://github.com/sdispater/pendulum", None, None),
        ),
        (
            "git+https://github.com/sdispater/pendulum#7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
            GitUrl(
                "https://github.com/sdispater/pendulum",
                "7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
                None,
            ),
        ),
        (
            "git+ssh://git@git.example.com:b/b.git#v1.0.0",
            GitUrl("git@git.example.com:b/b.git", "v1.0.0", None),
        ),
        (
            "git+ssh://git@github.com:sdispater/pendulum.git#foo/bar",
            GitUrl("git@github.com:sdispater/pendulum.git", "foo/bar", None),
        ),
        ("git+file:///foo/bar.git", GitUrl("file:///foo/bar.git", None, None)),
        (
            "git+file://C:\\Users\\hello\\testing.git#zkat/windows-files",
            GitUrl("file://C:\\Users\\hello\\testing.git", "zkat/windows-files", None),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git",
            GitUrl("https://git.example.com/sdispater/project/my_repo.git", None, None),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git",
            GitUrl("git@git.example.com:sdispater/project/my_repo.git", None, None),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git?subdirectory=path/to/package",
            GitUrl(
                "https://git.example.com/sdispater/project/my_repo.git",
                None,
                "path/to/package",
            ),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git?subdirectory=path/to/package",
            GitUrl(
                "git@git.example.com:sdispater/project/my_repo.git",
                None,
                "path/to/package",
            ),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git#dev?subdirectory=path/to/package",
            GitUrl(
                "https://git.example.com/sdispater/project/my_repo.git",
                "dev",
                "path/to/package",
            ),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git#dev?subdirectory=path/to/package",
            GitUrl(
                "git@git.example.com:sdispater/project/my_repo.git",
                "dev",
                "path/to/package",
            ),
        ),
    ],
)
def test_normalize_url(url, normalized):
    assert normalized == Git.normalize_url(url)


@pytest.mark.parametrize(
    "url, parsed",
    [
        (
            "git+ssh://user@hostname:project.git#commit",
            ParsedUrl(
                "ssh",
                "hostname",
                ":project.git",
                "user",
                None,
                "project",
                "commit",
                None,
            ),
        ),
        (
            "git+http://user@hostname/project/blah.git@commit",
            ParsedUrl(
                "http",
                "hostname",
                "/project/blah.git",
                "user",
                None,
                "blah",
                "commit",
                None,
            ),
        ),
        (
            "git+https://user@hostname/project/blah.git",
            ParsedUrl(
                "https",
                "hostname",
                "/project/blah.git",
                "user",
                None,
                "blah",
                None,
                None,
            ),
        ),
        (
            "git+https://user@hostname/project~_-.foo/blah~_-.bar.git",
            ParsedUrl(
                "https",
                "hostname",
                "/project~_-.foo/blah~_-.bar.git",
                "user",
                None,
                "blah~_-.bar",
                None,
                None,
            ),
        ),
        (
            "git+https://user@hostname:project/blah.git",
            ParsedUrl(
                "https",
                "hostname",
                ":project/blah.git",
                "user",
                None,
                "blah",
                None,
                None,
            ),
        ),
        (
            "git+ssh://git@github.com:sdispater/poetry.git#v1.0.27",
            ParsedUrl(
                "ssh",
                "github.com",
                ":sdispater/poetry.git",
                "git",
                None,
                "poetry",
                "v1.0.27",
                None,
            ),
        ),
        (
            "git+ssh://git@github.com:/sdispater/poetry.git",
            ParsedUrl(
                "ssh",
                "github.com",
                ":/sdispater/poetry.git",
                "git",
                None,
                "poetry",
                None,
                None,
            ),
        ),
        (
            "git+ssh://git@github.com:org/repo",
            ParsedUrl(
                "ssh", "github.com", ":org/repo", "git", None, "repo", None, None
            ),
        ),
        (
            "git+ssh://git@github.com/org/repo",
            ParsedUrl(
                "ssh", "github.com", "/org/repo", "git", None, "repo", None, None
            ),
        ),
        (
            "git+ssh://foo:22/some/path",
            ParsedUrl("ssh", "foo", "/some/path", None, "22", "path", None, None),
        ),
        (
            "git@github.com:org/repo",
            ParsedUrl(None, "github.com", ":org/repo", "git", None, "repo", None, None),
        ),
        (
            "git+https://github.com/sdispater/pendulum",
            ParsedUrl(
                "https",
                "github.com",
                "/sdispater/pendulum",
                None,
                None,
                "pendulum",
                None,
                None,
            ),
        ),
        (
            "git+https://github.com/sdispater/pendulum#7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
            ParsedUrl(
                "https",
                "github.com",
                "/sdispater/pendulum",
                None,
                None,
                "pendulum",
                "7a018f2d075b03a73409e8356f9b29c9ad4ea2c5",
                None,
            ),
        ),
        (
            "git+ssh://git@git.example.com:b/b.git#v1.0.0",
            ParsedUrl(
                "ssh", "git.example.com", ":b/b.git", "git", None, "b", "v1.0.0", None
            ),
        ),
        (
            "git+ssh://git@github.com:sdispater/pendulum.git#foo/bar",
            ParsedUrl(
                "ssh",
                "github.com",
                ":sdispater/pendulum.git",
                "git",
                None,
                "pendulum",
                "foo/bar",
                None,
            ),
        ),
        (
            "git+file:///foo/bar.git",
            ParsedUrl("file", None, "/foo/bar.git", None, None, "bar", None, None),
        ),
        (
            "git+file://C:\\Users\\hello\\testing.git#zkat/windows-files",
            ParsedUrl(
                "file",
                "C",
                ":\\Users\\hello\\testing.git",
                None,
                None,
                "testing",
                "zkat/windows-files",
                None,
            ),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git",
            ParsedUrl(
                "https",
                "git.example.com",
                "/sdispater/project/my_repo.git",
                None,
                None,
                "my_repo",
                None,
                None,
            ),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git",
            ParsedUrl(
                "ssh",
                "git.example.com",
                ":sdispater/project/my_repo.git",
                "git",
                None,
                "my_repo",
                None,
                None,
            ),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git?subdirectory=path/to/package",
            ParsedUrl(
                "https",
                "git.example.com",
                "/sdispater/project/my_repo.git",
                None,
                None,
                "my_repo",
                None,
                "path/to/package",
            ),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git?subdirectory=path/to/package",
            ParsedUrl(
                "ssh",
                "git.example.com",
                ":sdispater/project/my_repo.git",
                "git",
                None,
                "my_repo",
                None,
                "path/to/package",
            ),
        ),
        (
            "git+https://git.example.com/sdispater/project/my_repo.git#dev?subdirectory=path/to/package",
            ParsedUrl(
                "https",
                "git.example.com",
                "/sdispater/project/my_repo.git",
                None,
                None,
                "my_repo",
                "dev",
                "path/to/package",
            ),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git#dev?subdirectory=path/to/package",
            ParsedUrl(
                "ssh",
                "git.example.com",
                ":sdispater/project/my_repo.git",
                "git",
                None,
                "my_repo",
                "dev",
                "path/to/package",
            ),
        ),
    ],
)
def test_parse_url(url, parsed):
    result = ParsedUrl.parse(url)
    assert parsed.name == result.name
    assert parsed.pathname == result.pathname
    assert parsed.port == result.port
    assert parsed.protocol == result.protocol
    assert parsed.resource == result.resource
    assert parsed.rev == result.rev
    assert parsed.url == result.url
    assert parsed.user == result.user
    assert parsed.subdirectory == result.subdirectory


def test_parse_url_should_fail():
    url = "https://" + "@" * 64 + "!"

    with pytest.raises(ValueError):
        ParsedUrl.parse(url)

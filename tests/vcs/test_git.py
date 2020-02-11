import pytest

from poetry.vcs.git import Git
from poetry.vcs.git import GitUrl
from poetry.vcs.git import ParsedUrl


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
            "git+https://user@hostname/project~_-.foo/blah~_-.bar.git",
            GitUrl("https://user@hostname/project~_-.foo/blah~_-.bar.git", None),
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
        (
            "git+https://git.example.com/sdispater/project/my_repo.git",
            GitUrl("https://git.example.com/sdispater/project/my_repo.git", None),
        ),
        (
            "git+ssh://git@git.example.com:sdispater/project/my_repo.git",
            GitUrl("git@git.example.com:sdispater/project/my_repo.git", None),
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
                "ssh", "hostname", ":project.git", "user", None, "project", "commit"
            ),
        ),
        (
            "git+http://user@hostname/project/blah.git@commit",
            ParsedUrl(
                "http", "hostname", "/project/blah.git", "user", None, "blah", "commit"
            ),
        ),
        (
            "git+https://user@hostname/project/blah.git",
            ParsedUrl(
                "https", "hostname", "/project/blah.git", "user", None, "blah", None
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
            ),
        ),
        (
            "git+https://user@hostname:project/blah.git",
            ParsedUrl(
                "https", "hostname", ":project/blah.git", "user", None, "blah", None
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
            ),
        ),
        (
            "git+ssh://git@github.com:org/repo",
            ParsedUrl("ssh", "github.com", ":org/repo", "git", None, "repo", None),
        ),
        (
            "git+ssh://git@github.com/org/repo",
            ParsedUrl("ssh", "github.com", "/org/repo", "git", None, "repo", None),
        ),
        (
            "git+ssh://foo:22/some/path",
            ParsedUrl("ssh", "foo", "/some/path", None, "22", "path", None),
        ),
        (
            "git@github.com:org/repo",
            ParsedUrl(None, "github.com", ":org/repo", "git", None, "repo", None),
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
            ),
        ),
        (
            "git+ssh://git@git.example.com:b/b.git#v1.0.0",
            ParsedUrl("ssh", "git.example.com", ":b/b.git", "git", None, "b", "v1.0.0"),
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
            ),
        ),
        (
            "git+file:///foo/bar.git",
            ParsedUrl("file", None, "/foo/bar.git", None, None, "bar", None),
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


def test_parse_url_should_fail():
    url = "https://" + "@" * 64 + "!"

    with pytest.raises(ValueError):
        ParsedUrl.parse(url)

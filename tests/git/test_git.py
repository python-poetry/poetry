from poetry.vcs import Git
from poetry.vcs.git import GitConfig


def test_git_init():
    git = Git()
    assert isinstance(git, Git)
    assert isinstance(git.config, GitConfig)
    assert git._work_dir is None


def test_git_tags(git_tags):
    # tags are mocked in git_mock (tests/conftest.py)
    git = Git()
    assert git.tags() == git_tags

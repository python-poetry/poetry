from clikit.io import NullIO

from poetry.masonry.builders.builder import Builder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv


def test_builder_find_excluded_files(mocker):
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = []

    builder = Builder(
        Poetry.create(Path(__file__).parent / "fixtures" / "complete"),
        NullEnv(),
        NullIO(),
    )

    assert builder.find_excluded_files() == {"my_package/sub_pkg1/extra_file.xml"}

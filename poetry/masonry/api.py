"""
PEP-517 compliant buildsystem API
"""
import logging
import sys

from clikit.io import NullIO

from poetry.factory import Factory
from poetry.utils._compat import Path
from poetry.utils._compat import unicode
from poetry.utils.env import SystemEnv

from .builders.sdist import SdistBuilder
from .builders.wheel import WheelBuilder


log = logging.getLogger(__name__)


def get_requires_for_build_wheel(config_settings=None):
    """
    Returns an additional list of requirements for building, as PEP508 strings,
    above and beyond those specified in the pyproject.toml file.

    This implementation is optional. At the moment it only returns an empty list, which would be the same as if
    not define. So this is just for completeness for future implementation.
    """

    return []


# For now, we require all dependencies to build either a wheel or an sdist.
get_requires_for_build_sdist = get_requires_for_build_wheel


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    poetry = Factory().create_poetry(Path("."))
    builder = WheelBuilder(poetry, SystemEnv(Path(sys.prefix)), NullIO())

    dist_info = Path(metadata_directory, builder.dist_info)
    dist_info.mkdir(parents=True, exist_ok=True)

    if "scripts" in poetry.local_config or "plugins" in poetry.local_config:
        with (dist_info / "entry_points.txt").open("w", encoding="utf-8") as f:
            builder._write_entry_points(f)

    with (dist_info / "WHEEL").open("w", encoding="utf-8") as f:
        builder._write_wheel_file(f)

    with (dist_info / "METADATA").open("w", encoding="utf-8") as f:
        builder._write_metadata_file(f)

    return dist_info.name


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Builds a wheel, places it in wheel_directory"""
    poetry = Factory().create_poetry(Path("."))

    return unicode(
        WheelBuilder.make_in(
            poetry, SystemEnv(Path(sys.prefix)), NullIO(), Path(wheel_directory)
        )
    )


def build_sdist(sdist_directory, config_settings=None):
    """Builds an sdist, places it in sdist_directory"""
    poetry = Factory().create_poetry(Path("."))

    path = SdistBuilder(poetry, SystemEnv(Path(sys.prefix)), NullIO()).build(
        Path(sdist_directory)
    )

    return unicode(path.name)

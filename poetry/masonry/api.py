"""
PEP-517 compliant buildsystem API
"""
import logging
from pathlib import Path

from poetry.poetry import Poetry
from poetry.io import NullIO
from poetry.utils.venv import Venv

from .builders import SdistBuilder
from .builders import WheelBuilder

log = logging.getLogger(__name__)

# PEP 517 specifies that the CWD will always be the source tree
poetry = Poetry.create(".")


def get_requires_for_build_wheel(config_settings=None):
    """
    Returns a list of requirements for building, as strings
    """
    main, extras = SdistBuilder.convert_dependencies(poetry.package.requires)

    return main + extras


# For now, we require all dependencies to build either a wheel or an sdist.
get_requires_for_build_sdist = get_requires_for_build_wheel


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Builds a wheel, places it in wheel_directory"""
    info = WheelBuilder.make_in(poetry, NullIO(), Path(wheel_directory))

    return info.file.name


def build_sdist(sdist_directory, config_settings=None):
    """Builds an sdist, places it in sdist_directory"""
    path = SdistBuilder(poetry, Venv(), NullIO()).build(Path(sdist_directory))

    return path.name

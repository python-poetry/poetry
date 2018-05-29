import os
import sys

_ROOT = os.path.dirname(os.path.realpath(__file__))
_VENDOR = os.path.join(_ROOT, "_vendor")

# Add vendored dependencies to path.
sys.path.insert(0, _VENDOR)

from .__version__ import __version__  # noqa

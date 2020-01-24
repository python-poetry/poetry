import os
import sys

from .__version__ import __version__  # noqa


_ROOT = os.path.dirname(os.path.realpath(__file__))
_VENDOR = os.path.join(_ROOT, "_vendor")
_CURRENT_VENDOR = os.path.join(
    _VENDOR, "py{}".format(".".join(str(v) for v in sys.version_info[:2]))
)

# Add vendored dependencies to path.
sys.path.insert(0, _CURRENT_VENDOR)

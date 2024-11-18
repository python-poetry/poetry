from __future__ import annotations

import logging
import sys

from poetry.config.config import Config


logger = logging.getLogger(__name__)


def _is_truststore_available() -> bool:
    if sys.version_info < (3, 10):
        logger.debug("Disabling truststore because Python version isn't 3.10+")
        return False

    try:
        import ssl  # noqa: F401
    except ImportError:
        logger.warning("Disabling truststore since ssl support is missing")
        return False

    try:
        import truststore  # noqa: F401
    except ImportError:
        logger.warning("Disabling truststore because `truststore` package is missing`")
        return False
    return True


def is_truststore_enabled() -> bool:
    return Config.create().get("system-truststore") and _is_truststore_available()

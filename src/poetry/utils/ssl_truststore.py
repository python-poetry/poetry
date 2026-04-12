from __future__ import annotations

from poetry.config.config import Config


def is_truststore_enabled() -> bool:
    is_ssl_available = True
    try:
        import ssl  # noqa: F401
    except ImportError:
        import logging

        logger = logging.getLogger(__name__)

        logger.warning("Disabling truststore since ssl support is missing")
        is_ssl_available = False

    return Config.create().get("system-truststore") and is_ssl_available

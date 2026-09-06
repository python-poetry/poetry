from __future__ import annotations

import os

from requests_toolbelt import user_agent as requests_user_agent

from poetry.__version__ import __version__


def get_user_agent() -> str:
    """Build Poetry's User-Agent, including optional caller context."""
    extras: list[tuple[str, str]] = []
    user_data = os.environ.get("POETRY_USER_AGENT_USER_DATA")
    if user_data is not None:
        extras.append(("user_data", user_data))

    return requests_user_agent("poetry", __version__, extras=extras)

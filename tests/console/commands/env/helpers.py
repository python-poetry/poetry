from __future__ import annotations

from pathlib import Path
from typing import Any


def build_venv(path: Path | str, **_: Any) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

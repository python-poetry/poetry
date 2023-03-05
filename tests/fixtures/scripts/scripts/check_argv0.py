from __future__ import annotations

import sys

from pathlib import Path


def main() -> int:
    path = Path(sys.argv[0])
    if sys.argv[0] == sys.argv[1]:
        if path.is_absolute() and not path.exists():
            raise RuntimeError(f"sys.argv[0] does not exist: {path}")
    else:
        raise RuntimeError(
            f"unexpected sys.argv[0]: '{sys.argv[0]}', should be '{sys.argv[1]}'"
        )

    return 0


if __name__ == "__main__":
    raise sys.exit(main())

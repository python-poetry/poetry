from __future__ import annotations

import sys
import os

if __name__ == "__main__":
    # Explicitly remove PYTHONUSERBASE from sys.path without touching PYTHONPATH.
    # We may need additional libraries supplied by the environment, but we should
    # do our best to insulate ourselves from the user's site-packages.
    #
    # Unfortunately, `poetry remove` delegates to `pip uninstall`, so simply
    # removing PYTHONUSERBASE from PYTHONPATH will prevent anything from
    # being uninstalled.
    userbase = os.getenv('PYTHONUSERBASE')
    if userbase:
        sys.path = [x for x in sys.path if not x.startswith(userbase)]

    from poetry.console.application import main

    sys.exit(main())

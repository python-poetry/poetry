from __future__ import annotations

import sys
import os

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

# Re-export main in a way that Pyright doesn't complain about
import poetry.console.application
main = poetry.console.application.main

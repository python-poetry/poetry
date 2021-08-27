try:
    import zipp
except ImportError:
<<<<<<< HEAD
    import zipfile as zipp  # noqa: F401, TC002

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # noqa: F401, TC002
=======
    import zipfile as zipp  # noqa
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

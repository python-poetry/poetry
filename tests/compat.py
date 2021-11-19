try:
    import zipp
except ImportError:
    import zipfile as zipp  # noqa: F401, TC002

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # noqa: F401, TC002

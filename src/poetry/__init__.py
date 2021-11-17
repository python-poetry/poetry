from pkgutil import extend_path
from typing import List  # noqa: TC002


__path__: List[str] = extend_path(__path__, __name__)

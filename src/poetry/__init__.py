from pkgutil import extend_path
from typing import List


__path__: List[str] = extend_path(__path__, __name__)

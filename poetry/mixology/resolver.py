from typing import Any
from typing import List
from typing import Union

from .contracts import SpecificationProvider
from .contracts import UI
from .dependency_graph import DependencyGraph
from .resolution import Resolution


class Resolver:

    def __init__(self,
                 specification_provider,  # type: SpecificationProvider
                 resolver_ui              # type: UI
                 ):
        self._specification_provider = specification_provider
        self._resolver_ui = resolver_ui

    @property
    def specification_provider(self):  # type: () -> SpecificationProvider
        return self._specification_provider

    @property
    def ui(self):  # type: () -> UI
        return self._resolver_ui

    def resolve(self,
                requested,  # type: List[Any]
                base=None   # type: Union[DependencyGraph, None]
                ):  # type: (...) -> DependencyGraph
        if base is None:
            base = DependencyGraph()

        return Resolution(
            self._specification_provider,
            self._resolver_ui,
            requested,
            base
        ).resolve()

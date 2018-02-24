from typing import Any
from typing import List
from typing import Union

from .contracts import SpecificationProvider
from .contracts import UI
from .dependency_graph import DependencyGraph
from .resolution import Resolution


class Resolver:

    def __init__(self,
                 specification_provider: SpecificationProvider,
                 resolver_ui: UI):
        self._specification_provider = specification_provider
        self._resolver_ui = resolver_ui

    @property
    def specification_provider(self) -> SpecificationProvider:
        return self._specification_provider

    @property
    def ui(self) -> UI:
        return self._resolver_ui

    def resolve(self,
                requested: List[Any],
                base: Union[DependencyGraph, None] = None) -> DependencyGraph:
        if base is None:
            base = DependencyGraph()

        return Resolution(
            self._specification_provider,
            self._resolver_ui,
            requested,
            base
        ).resolve()

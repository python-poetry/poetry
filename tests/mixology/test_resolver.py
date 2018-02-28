import json
import os
import pytest

from poetry.mixology import DependencyGraph
from poetry.mixology import Resolver
from poetry.mixology.exceptions import CircularDependencyError
from poetry.mixology.exceptions import ResolverError
from poetry.mixology.exceptions import VersionConflict
from poetry.packages import Dependency

from .index import Index
from .ui import UI

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
FIXTURE_CASE_DIR = os.path.join(FIXTURE_DIR, 'case')


@pytest.fixture()
def resolver():
    return Resolver(Index.from_fixture('awesome'), UI(True))


class Case:

    def __init__(self, fixture):
        self._fixture = fixture
        self.name = fixture['name']
        self._requested = None
        self._result = None
        self._index = None
        self._base = None
        self._conflicts = None

    @property
    def requested(self):
        if self._requested is not None:
            return self._requested

        requested = []
        for name, requirement in self._fixture['requested'].items():
            requested.append(Dependency(name, requirement))

        self._requested = requested

        return self._requested

    @property
    def result(self):
        if self._result is not None:
            return self._result

        graph = DependencyGraph()
        for resolved in self._fixture['resolved']:
            self.add_dependencies_to_graph(graph, None, resolved)

        self._result = graph

        return self._result

    @property
    def index(self):
        if self._index is None:
            self._index = Index.from_fixture(
                self._fixture.get('index', 'awesome')
            )

        return self._index

    @property
    def base(self):
        if self._base is not None:
            return self._base

        graph = DependencyGraph()
        for r in self._fixture['base']:
            self.add_dependencies_to_graph(graph, None, r)

        self._base = graph

        return self._base

    @property
    def conflicts(self):
        if self._conflicts is None:
            self._conflicts = self._fixture['conflicts']

        return self._conflicts

    def add_dependencies_to_graph(self, graph, parent, data, all_parents=None):
        if all_parents is None:
            all_parents = set()

        name = data['name']
        version = data['version']
        dependency = [s for s in self.index.packages[name] if s.version == version][0]
        if parent:
            vertex = graph.add_vertex(name, dependency)
            graph.add_edge(parent, vertex, dependency)
        else:
            vertex = graph.add_vertex(name, dependency, True)

        if vertex in all_parents:
            return

        for dep in data['dependencies']:
            self.add_dependencies_to_graph(graph, vertex, dep, all_parents)


def case(name):
    with open(os.path.join(FIXTURE_CASE_DIR, name + '.json')) as fd:
        return Case(json.load(fd))


def assert_graph(dg, result):
    packages = sorted(dg.vertices.values(), key=lambda x: x.name)
    expected_packages = sorted(result.vertices.values(), key=lambda x: x.name)

    assert packages == expected_packages


@pytest.mark.parametrize(
    'fixture',
    [
        'empty',
        'simple',
        'simple_with_base',
        'simple_with_dependencies',
        'simple_with_shared_dependencies',
        'django',
    ]
)
def test_resolver(fixture):
    c = case(fixture)
    resolver = Resolver(c.index, UI(True))
    dg = resolver.resolve(c.requested, base=c.base)

    assert_graph(dg, c.result)


@pytest.mark.parametrize(
    'fixture',
    [
        'circular',
        'unresolvable_child'
    ]
)
def test_resolver_fail(fixture):
    c = case(fixture)
    resolver = Resolver(c.index, UI())

    with pytest.raises(ResolverError) as e:
        resolver.resolve(c.requested, base=c.base)

    names = []
    e = e.value
    if isinstance(e, CircularDependencyError):
        names = [d.name for d in e.dependencies]
    elif isinstance(e, VersionConflict):
        names = [n for n in e.conflicts.keys()]

    assert sorted(names) == sorted(c.conflicts)

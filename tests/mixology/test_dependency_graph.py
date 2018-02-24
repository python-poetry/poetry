import pytest

from poetry.mixology import DependencyGraph


@pytest.fixture()
def graph():
    graph = DependencyGraph()

    return graph


@pytest.fixture()
def root(graph):
    return graph.add_vertex('Root', 'Root', True)


@pytest.fixture()
def root2(graph):
    return graph.add_vertex('Root2', 'Root2', True)


@pytest.fixture()
def child(graph):
    return graph.add_child_vertex('Child', 'Child', ['Root'], 'Child')


def test_root_vertex_named(graph, root, root2, child):
    assert graph.root_vertex_named('Root') is root


def test_vertex_named(graph, root, root2, child):
    assert graph.vertex_named('Root') is root
    assert graph.vertex_named('Root2') is root2
    assert graph.vertex_named('Child') is child


def test_root_vertex_named_non_existent(graph):
    assert graph.root_vertex_named('missing') is None


def test_vertex_named_non_existent(graph):
    assert graph.vertex_named('missing') is None


def test_detach_vertex_without_successors(graph):
    root = graph.add_vertex('root', 'root', True)
    graph.detach_vertex_named(root.name)
    assert graph.vertex_named(root.name) is None
    assert len(graph.vertices) == 0


def test_detach_vertex_with_successors(graph):
    root = graph.add_vertex('root', 'root', True)
    child = graph.add_child_vertex('child', 'child', ['root'], 'child')
    graph.detach_vertex_named(root.name)

    assert graph.vertex_named(root.name) is None
    assert graph.vertex_named(child.name) is None
    assert len(graph.vertices) == 0


def test_detach_vertex_with_successors_with_other_parents(graph):
    root = graph.add_vertex('root', 'root', True)
    root2 = graph.add_vertex('root2', 'root2', True)
    child = graph.add_child_vertex('child', 'child', ['root', 'root2'], 'child')
    graph.detach_vertex_named(root.name)

    assert graph.vertex_named(root.name) is None
    assert graph.vertex_named(child.name) is child
    assert child.predecessors == [root2]
    assert len(graph.vertices) == 2


def test_detach_vertex_with_predecessors(graph):
    parent = graph.add_vertex('parent', 'parent', True)
    child = graph.add_child_vertex('child', 'child', ['parent'], 'child')
    graph.detach_vertex_named(child.name)

    assert graph.vertex_named(child.name) is None
    assert graph.vertices == {parent.name: parent}
    assert len(parent.outgoing_edges) == 0


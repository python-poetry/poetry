from .exceptions import CircularDependencyError
from .graph.log import Log


class DependencyGraph:

    def __init__(self):
        self._vertices = {}
        self._log = Log()

    @property
    def vertices(self):
        return self._vertices

    @property
    def log(self):
        return self._log

    def tag(self, tag):
        return self._log.tag(self, tag)

    def rewind_to(self, tag):
        return self._log.rewind_to(self, tag)

    def add_child_vertex(self, name, payload, parent_names, requirement):
        root = True

        try:
            parent_names.index(None)
        except ValueError:
            root = False

        parent_names = [n for n in parent_names if n is not None]
        vertex = self.add_vertex(name, payload, root)
        if root:
            vertex.explicit_requirements.append(requirement)

        for parent_name in parent_names:
            parent_vertex = self.vertex_named(parent_name)
            self.add_edge(parent_vertex, vertex, requirement)

        return vertex

    def add_vertex(self, name, payload, root=False):
        return self._log.add_vertex(self, name, payload, root)

    def detach_vertex_named(self, name):
        return self._log.detach_vertex_named(self, name)

    def vertex_named(self, name):
        return self.vertices.get(name)

    def root_vertex_named(self, name):
        vertex = self.vertex_named(name)
        if vertex and vertex.root:
            return vertex

    def add_edge(self, origin, destination, requirement):
        if destination.has_path_to(origin):
            raise CircularDependencyError([origin, destination])

        return self.add_edge_no_circular(origin, destination, requirement)

    def add_edge_no_circular(self, origin, destination, requirement):
        self._log.add_edge_no_circular(
            self,
            origin.name, destination.name,
            requirement
        )

    def delete_edge(self, edge):
        return self._log.delete_edge(
            self,
            edge.origin.name,
            edge.destination.name,
            edge.requirement
        )

    def set_payload(self, name, payload):
        return self._log.set_payload(self, name, payload)

    def to_dot(self):
        dot_vertices = []
        dot_edges = []

        for n, v in self.vertices.items():
            dot_vertices.append(
                '  {} [label="{}|{}"]'.format(n, n, v.payload or '')
            )
            for e in v.outgoing_edges:
                label = e.requirement
                dot_edges.append(
                    '  {} -> {} [label="{}"]'.format(
                        e.origin.name,
                        e.destination.name,
                        label
                    )
                )

        dot_vertices = sorted(set(dot_vertices))
        dot_edges = sorted(set(dot_edges))

        dot_vertices.insert(0, 'digraph G {')
        dot_vertices.append('')
        dot_edges.append('}')

        dot = dot_vertices + dot_edges

        return '\n'.join(dot)

    def __iter__(self):
        return iter(self.vertices.values())

from .action import Action


class DetachVertexNamed(Action):

    def __init__(self, name):
        super(DetachVertexNamed, self).__init__()

        self._name = name
        self._vertex = None

    @property
    def action_name(self):
        return 'detach_vertex'

    @property
    def name(self):
        return self._name

    def up(self, graph):
        if self._name not in graph.vertices:
            return []

        self._vertex = graph.vertices[self._name]
        del graph.vertices[self._name]
        removed_vertices = [self._vertex]
        for e in self._vertex.outgoing_edges:
            v = e.destination
            try:
                v.incoming_edges.remove(e)
            except ValueError:
                pass

            if not v.root and not v.incoming_edges:
                removed_vertices += graph.detach_vertex_named(v.name)

        for e in self._vertex.incoming_edges:
            v = e.origin

            try:
                v.outgoing_edges.remove(e)
            except ValueError:
                pass

        return removed_vertices

    def down(self, graph):
        if self._vertex is None:
            return

        graph.vertices[self._vertex.name] = self._vertex
        for e in self._vertex.outgoing_edges:
            e.destination.incoming_edges.append(e)

        for e in self._vertex.incoming_edges:
            e.origin.outgoing_edges.append(e)

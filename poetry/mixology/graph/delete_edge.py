from .action import Action
from .edge import Edge


class DeleteEdge(Action):

    def __init__(self, origin, destination, requirement):
        super(DeleteEdge, self).__init__()

        self._origin = origin
        self._destination = destination
        self._requirement = requirement

    @property
    def action_name(self):
        return 'delete_edge'

    @property
    def origin(self):
        return self._origin

    @property
    def destination(self):
        return self._destination

    @property
    def requirement(self):
        return self._requirement

    def up(self, graph):
        edge = self.make_edge(graph)
        self._delete_first(edge.origin.outgoing_edges, edge)
        self._delete_first(edge.destination.incoming_edges, edge)

        return edge

    def down(self, graph):
        edge = self.make_edge(graph)
        edge.origin.outgoing_edges.append(edge)
        edge.origin.incoming_edges.append(edge)

    def make_edge(self, graph):
        return Edge(
            graph.vertex_named(self._origin),
            graph.vertex_named(self._destination),
            self._requirement
        )

    def _delete_first(self, elements, element):
        """
        :type elements: list
        """
        try:
            index = elements.index(element)
        except ValueError:
            return

        del elements[index]

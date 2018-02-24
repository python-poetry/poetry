from .add_edge_no_circular import AddEdgeNoCircular
from .add_vertex import AddVertex
from .delete_edge import DeleteEdge
from .detach_vertex_named import DetachVertexNamed
from .set_payload import SetPayload
from .tag import Tag


class Log:
    """
    A log for dependency graph actions.
    """

    def __init__(self):
        self._current_action = None
        self._first_action = None

    def tag(self, graph, tag):
        """
        Tags the current state of the dependency as the given tag.
        """
        return self._push_action(graph, Tag(tag))

    def add_vertex(self, graph, name, payload, root):
        return self._push_action(graph, AddVertex(name, payload, root))

    def detach_vertex_named(self, graph, name):
        return self._push_action(graph, DetachVertexNamed(name))

    def add_edge_no_circular(self, graph, origin, destination, requirement):
        action = AddEdgeNoCircular(origin, destination, requirement)
        return self._push_action(graph, action)

    def delete_edge(self, graph, origin, destination, requirement):
        action = DeleteEdge(origin, destination, requirement)
        return self._push_action(graph, action)

    def set_payload(self, graph, name, payload):
        return self._push_action(graph, SetPayload(name, payload))

    def pop(self, graph):
        action = self._current_action
        if not action:
            return

        self._current_action = action.previous
        if not self._current_action:
            self._first_action = None

        action.down(graph)

        return action

    def rewind_to(self, graph, tag):
        while True:
            action = self.pop(graph)
            if not action:
                raise ValueError('No tag "{}" found'.format(tag))

            if isinstance(action, Tag) and action.tag == tag:
                break

    def _push_action(self, graph, action):
        """
        Adds the given action to the log, running the action

        :param graph: The graph
        :param action: The action
        :type action: Action
        """
        action.previous = self._current_action
        if self._current_action:
            self._current_action.next = action

        self._current_action = action
        if not self._first_action:
            self._first_action = action

        return action.up(graph)

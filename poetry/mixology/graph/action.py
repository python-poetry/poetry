from typing import Any


class Action(object):

    def __init__(self):
        self.previous = None
        self.next = None

    @property
    def action_name(self):  # type: () -> str
        raise NotImplementedError()

    def up(self, graph):  # type: (DependencyGraph) -> Any
        """
        Performs the action on the given graph.
        """
        raise NotImplementedError()

    def down(self, graph):  # type: (DependencyGraph) -> None
        """
        Reverses the action on the given graph.
        """
        raise NotImplementedError()

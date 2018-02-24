from typing import Any


class Action:

    def __init__(self):
        self.previous = None
        self.next = None

    @property
    def action_name(self) -> str:
        raise NotImplementedError()

    def up(self, graph: 'DependencyGraph') -> Any:
        """
        Performs the action on the given graph.
        """
        raise NotImplementedError()

    def down(self, graph: 'DependencyGraph') -> None:
        """
        Reverses the action on the given graph.
        """
        raise NotImplementedError()

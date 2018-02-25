from .action import Action
from .vertex import Vertex

_NULL = object()


class AddVertex(Action):

    def __init__(self, name, payload, root):
        """
        :param name: The name of the vertex.
        :type name: str

        :param payload: The payload of he vertex
        :type payload: Any

        :param root: whether the vertex is root or not
        :type root: bool
        """
        super(AddVertex, self).__init__()

        self._name = name
        self._payload = payload
        self._root = root
        self._existing_payload = _NULL
        self._existing_root = None

    @property
    def action_name(self):
        return 'add_vertex'

    @property
    def name(self):
        return self._name

    @property
    def payload(self):
        return self._payload

    @property
    def root(self):
        return self._root

    def up(self, graph):
        existing = graph.vertices.get(self._name)
        if existing:
            self._existing_payload = existing.payload
            self._existing_root = existing.root

        vertex = existing or Vertex(self._name, self._payload)
        graph.vertices[vertex.name] = vertex
        if not vertex.payload:
            vertex.payload = self.payload

        if not vertex.root:
            vertex.root = self.root

        return vertex

    def down(self, graph):
        if self._existing_payload is not _NULL:
            vertex = graph.vertices[self._name]
            vertex.payload = self._existing_payload
            vertex.root = self._existing_root
        else:
            del graph.vertices[self._name]

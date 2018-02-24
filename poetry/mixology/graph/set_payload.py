from .action import Action


class SetPayload(Action):

    def __init__(self, name, payload):
        super(SetPayload, self).__init__()

        self._name = name
        self._payload = payload
        self._old_payload = None

    @property
    def action_name(self):
        return 'set_payload'

    @property
    def name(self):
        return self._name

    @property
    def payload(self):
        return self._payload

    def up(self, graph):
        vertex = graph.vertex_named(self._name)
        self._old_payload = vertex.payload
        vertex.payload = self._payload

    def down(self, graph):
        graph.vertex_named(self._name).payload = self._old_payload

from ..utils import unique

class Vertex:

    def __init__(self, name, payload):
        self.name = name
        self.payload = payload
        self.root = False
        self._explicit_requirements = []
        self.outgoing_edges = []
        self.incoming_edges = []

    @property
    def explicit_requirements(self):
        return self._explicit_requirements
        
    @property
    def requirements(self):
        return unique([
            edge.requirement for edge in self.incoming_edges
        ] + self._explicit_requirements)
    
    @property
    def predecessors(self):
        return [edge.origin for edge in self.incoming_edges]

    @property
    def recursive_predecessors(self):
        return self._recursive_predecessors()

    def _recursive_predecessors(self, vertices=None):
        if vertices is None:
            vertices = set()

        for edge in self.incoming_edges:
            vertex = edge.origin

            if vertex in vertices:
                continue

            vertices.add(vertex)
            vertex._recursive_predecessors(vertices)

        return vertices

    @property
    def successors(self):
        return [
            edge.destination for edge in self.outgoing_edges
        ]

    @property
    def recursive_successors(self):
        return self._recursive_successors()

    def _recursive_successors(self, vertices=None):
        if vertices is None:
            vertices = set()

        for edge in self.outgoing_edges:
            vertex = edge.destination

            if vertex in vertices:
                continue

            vertices.add(vertex)
            vertex._recursive_successors(vertices)

        return vertices

    def __eq__(self, other):
        if not isinstance(other, Vertex):
            return NotImplemented

        if self is other:
            return True

        return (
            self.name == other.name
            and self.payload == other.payload
            and set(self.successors) == set(other.successors)
        )

    def __hash__(self):
        return hash(self.name)

    def has_path_to(self, other):
        return (
            self == other
            or any([v.has_path_to(other) for v in self.successors])
        )

    def is_ancestor(self, other):
        return other.path_to(self)

    def __repr__(self):
        return '<Vertex {} ({})>'.format(self.name, self.payload)

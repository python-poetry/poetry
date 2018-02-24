from .action import Action


class Tag(Action):

    def __init__(self, tag):
        super(Tag, self).__init__()

        self._tag = tag

    @property
    def action_name(self):
        return 'tag'

    @property
    def tag(self):
        return self._tag

    def up(self, graph):
        pass

    def down(self, graph):
        pass

class PossibilitySet:

    def __init__(self, dependencies, possibilities):
        self.dependencies = dependencies
        self.possibilities = possibilities

    @property
    def latest_version(self):
        if self.possibilities:
            return self.possibilities[-1]

    def __str__(self):
        return '[{}]'.format(', '.join([str(p) for p in self.possibilities]))

    def __repr__(self):
        return f'<PossibilitySet {str(self)}>'

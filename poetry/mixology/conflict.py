class Conflict:

    def __init__(self,
                 requirement,
                 requirements,
                 existing,
                 possibility_set,
                 locked_requirement,
                 requirement_trees,
                 activated_by_name,
                 underlying_error):
        self.requirement = requirement
        self.requirements = requirements
        self.existing = existing
        self.possibility_set = possibility_set
        self.locked_requirement = locked_requirement
        self.requirement_trees = requirement_trees,
        self.activated_by_name = activated_by_name
        self.underlying_error = underlying_error

    @property
    def possibility(self):
        if self.possibility_set and self.possibility_set.latest_version:
            return self.possibility_set.latest_version

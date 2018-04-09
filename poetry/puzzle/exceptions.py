class SolverProblemError(Exception):

    def __init__(self, error):
        self._error = error

        super(SolverProblemError, self).__init__(str(error))

    @property
    def error(self):
        return self._error

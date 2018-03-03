
class InvalidElementError(Exception):
    """
    Raised by Element factories when the given sequence of tokens or sub-elements are invalid for the
    specific type of Element being created.
    """

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return "InvalidElementError: {}".format(self.message)


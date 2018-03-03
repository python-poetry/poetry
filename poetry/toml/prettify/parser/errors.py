from ..errors import TOMLError


class ParsingError(TOMLError):

    def __init__(self, message='', token=None):
        self.message = message
        self.token = token

    def __repr__(self):
        if self.message and self.token:
            return "{} at row {} and col {}".format(
                self.message, self.token.row, self.token.col
            )
        else:
            return self.message

    def __str__(self):
        return repr(self)

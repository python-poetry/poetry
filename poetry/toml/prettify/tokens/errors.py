from ..errors import TOMLError


class DeserializationError(TOMLError):
    pass


class BadEscapeCharacter(TOMLError):
    pass


class MalformedDateError(DeserializationError):
    pass

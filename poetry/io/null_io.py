from cleo.io.io_mixin import IOMixin
from clikit.io import NullIO as BaseNullIO


class NullIO(IOMixin, BaseNullIO):
    """
    A wrapper around CliKit's NullIO.
    """

    def __init__(self, *args, **kwargs):
        super(NullIO, self).__init__(*args, **kwargs)

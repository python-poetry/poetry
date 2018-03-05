from .sdist import SdistBuilder


class CompleteBuilder:

    def __init__(self, poetry):
        self._poetry = poetry

    def build(self):
        # We start by building the tarball
        # We will use it to build the wheel
        sdist_builder = SdistBuilder(self._poetry)
        sdist_file = sdist_builder.build()

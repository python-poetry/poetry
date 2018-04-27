import pytest

from poetry.console import Application as BaseApplication
from poetry.utils._compat import Path


class Application(BaseApplication):

    def __init__(self, poetry_path):
        super(Application, self).__init__()

        self._poetry_path = poetry_path

    @property
    def poetry(self):
        from poetry.poetry import Poetry

        if self._poetry is not None:
            return self._poetry

        self._poetry = Poetry.create(self._poetry_path)

        return self._poetry


@pytest.fixture
def app():
    return Application(
        Path(__file__).parent.parent / 'fixtures' / 'sample_project'
    )

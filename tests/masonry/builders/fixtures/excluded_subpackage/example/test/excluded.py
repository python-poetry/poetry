<<<<<<< HEAD
from tests.masonry.builders.fixtures.excluded_subpackage.example import __version__
=======
from .. import __version__
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)


def test_version():
    assert __version__ == "0.1.0"

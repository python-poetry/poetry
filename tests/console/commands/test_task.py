from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.poetry import Poetry


def test_task(app):
    app._poetry = Poetry.create(
        Path(__file__).parent.parent.parent / "fixtures" / "project_with_tasks"
    )
    command = app.find("task")
    tester = CommandTester(command)

    tester.execute("task echo")

    path = Path(".temp/poetry_test_task.txt")
    with path.open("r") as f:
        assert "Hello World!" in f.read()

    # cleanup
    Path.unlink(path)
    Path.rmdir(path.parent)

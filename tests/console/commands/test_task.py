from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.poetry import Poetry


def test_task(app):
    app._poetry = Poetry.create(
        Path(__file__).parent.parent.parent / "fixtures" / "project_with_tasks"
    )
    command = app.find("task")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name()), ("task", "echo")])
    with open("/tmp/poetry_test_task.txt", "r") as f:
        assert f.read() == "Hello World!\n"

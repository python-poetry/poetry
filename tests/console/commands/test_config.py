import json
import os

from cleo.testers import CommandTester


def test_list_displays_default_value_if_not_set(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("--list")

    expected = """cache-dir = "/foo"
virtualenvs.create = true
virtualenvs.in-project = false
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_setting(app, config_source, config_document):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    expected = """cache-dir = "/foo"
virtualenvs.create = false
virtualenvs.in-project = false
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert expected == tester.io.fetch_output()


def test_display_single_setting(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create")

    expected = """true
"""

    assert expected == tester.io.fetch_output()

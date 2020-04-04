# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..conftest import Path


# rom cleo.testers import CommandTester


fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

# As this test needs changes in poetry_core at the time of writing it will fail
# in Github's checks. Local testing is possible.
#
# def test_export_with_vcs_subdirectory(app_project):
#     project = fixtures_dir / "project_with_git_subdirectory_dependency"
#     app = app_project(project)
#
#     command = app.find("lock")
#     tester = CommandTester(command)
#     tester.execute()
#
#     assert app.poetry.locker.lock.exists()
#
#     with app.poetry.locker.lock.open(encoding="utf-8") as f:
#         content = f.read()
#     expected = """\
# [[package]]
# category = "main"
# description = ""
# name = "demo"
# optional = false
# python-versions = "~2.7 || ^3.4"
# version = "0.1.2"
#
# [package.source]
# reference = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
# subdirectory = "pyproject-demo"
# type = "git"
# url = "https://github.com/demo/project_in_subdirectory.git"
#
# [metadata]
# content-hash = "1394d1b3da3a2a62939852f9b1671ad0b6a7dbb0c2e9f1017a0df9b30c8b151d"
# python-versions = "~2.7 || ^3.4"
#
# [metadata.files]
# demo = []
# """
#     assert content == expected

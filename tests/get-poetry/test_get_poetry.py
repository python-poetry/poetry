import os


def test_get_poetry():
    cmd = "cd {} && cat ../get-poetry.py | python".format(os.path.dirname(__file__))
    os.system(cmd)

import os
from pathlib import Path


def test_get_poetry():
    cmd = "cd {} && cat ../get-poetry.py | python3".format(Path(__file__).parent)
    os.system(cmd)

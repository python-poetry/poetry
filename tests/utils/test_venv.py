import pytest

from poetry.utils.venv import Venv, VenvError, VenvError
import sys
import os
from unittest.mock import MagicMock
from poetry.utils._compat import Path


"""
create :    change name
            pyversion

"""
global pp_arg


def test_create_set_venv_name_with_name(monkeypatch, tmpdir):
    monkeypatch.delenv('VIRTUAL_ENV')
    monkeypatch.setattr(Venv, 'build', lambda x,y: "rien")
    monkeypatch.setattr('poetry.utils.venv.Path', lambda x: tmpdir)
    a = Venv.create(io = MagicMock(), name="rien", py_version="2.7")
    assert os.environ['VIRTUAL_ENV'] == str(tmpdir.join("virtualenvs","rien-py2.7"))

def test_create_set_venv_name_without_name(monkeypatch, tmpdir):
    monkeypatch.delenv('VIRTUAL_ENV')
    monkeypatch.setattr(Venv, 'build', lambda x,y: "rien")

    path = MagicMock(return_value=Path(str(tmpdir)))
    mm = MagicMock()
    mm.name = "essai"
    path.cwd.return_value = mm
    monkeypatch.setattr('poetry.utils.venv.Path', path)

    a = Venv.create(io = MagicMock(), py_version="2.7")
    assert os.environ['VIRTUAL_ENV'] == str(tmpdir.join("virtualenvs","essai-py2.7"))

def test_create_set_venv_name_without_pyversion(monkeypatch, tmpdir):
    monkeypatch.delenv('VIRTUAL_ENV')
    monkeypatch.setattr(Venv, 'build', lambda x,y: "rien")
    monkeypatch.setattr('poetry.utils.venv.Path', lambda x: tmpdir)
    a = Venv.create(io = MagicMock(), name="rien")
    vv = sys.version[:3]
    assert os.environ['VIRTUAL_ENV'] == str(tmpdir.join("virtualenvs","rien-py"+vv))

def test_popen_args(tmpdir, monkeypatch):
    path = tmpdir.join("myenv")
    def mock(self):
        # argg
        global pp_arg
        self.kill()
        pp_arg =  self.args
        return (1,2)

    monkeypatch.setattr("poetry.utils.venv.Popen.communicate", mock)
    Venv.build(str(path))
    assert pp_arg[0] == 'python'+sys.version[:3]

    Venv.build(str(path), py_version='3.6')
    assert pp_arg == ['python3.6', '-m', 'venv', str(path)]

    Venv.build(str(path), py_version='2.7')
    assert pp_arg == ['python2.7', '-m', 'virtualenv', str(path)]

@pytest.mark.skipif(sys.version_info < (3,),reason="requires python3")
def test_python3_version_error(tmpdir):
    with pytest.raises(VenvError) as exc:
        Venv.build(str(tmpdir), py_version='2.10')
    assert str(exc.value) == 'Python version : 2.10 seems no to be installed on the system'

@pytest.mark.skipif(sys.version_info >= (3,),reason="requires python2.7")
def test_python2_version_error(tmpdir):
    with pytest.raises(VenvError) as exc:
        Venv.build(str(tmpdir), py_version='2.10')
    assert str(exc.value) == 'Python version : 2.10 seems no to be installed on the system'

from poetry.utils.shell import Shell


def test_name_and_path_properties():
    """
    Given a Shell object, check that???
    """
    s = Shell(name="name", path="path")
    assert s.name == s._name == "name"
    assert s.path == s._path == "path"

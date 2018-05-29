from poetry.toml.structurer import NamedDict
from poetry.toml.toplevels import Name
from poetry.toml.prettify.elements.table import TableElement


def test_named_dict():
    d = NamedDict()
    d[Name(("root", "sub1", "sub2"))] = "foo"

    assert d["root"]["sub1"]["sub2"] == "foo"
    assert d["root"] == {"sub1": {"sub2": "foo"}}

    d = NamedDict()
    d[Name(("root", "ns"))] = TableElement({})
    d[Name(("root", "ns", "sub2"))] = TableElement({})
    d[Name(("root", "ns", "sub3"))] = TableElement({})
    assert d["root"]["ns"]["sub2"] == {}
    assert d["root"]["ns"]["sub3"] == {}

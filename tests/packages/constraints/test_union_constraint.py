from poetry.packages.constraints.constraint import Constraint
from poetry.packages.constraints.union_constraint import UnionConstraint


def test_allows():
    c = UnionConstraint(Constraint("win32"), Constraint("linux"))

    assert c.allows(Constraint("win32"))
    assert c.allows(Constraint("linux"))
    assert not c.allows(Constraint("darwin"))


def test_allows_any():
    c = UnionConstraint(Constraint("win32"), Constraint("linux"))

    assert c.allows_any(c)
    assert c.allows_any(UnionConstraint(Constraint("win32"), Constraint("darwin")))
    assert not c.allows_any(UnionConstraint(Constraint("linux2"), Constraint("darwin")))
    assert c.allows_any(Constraint("win32"))
    assert not c.allows_any(Constraint("darwin"))


def test_allows_all():
    c = UnionConstraint(Constraint("win32"), Constraint("linux"))

    assert c.allows_all(c)
    assert not c.allows_all(UnionConstraint(Constraint("win32"), Constraint("darwin")))
    assert not c.allows_all(UnionConstraint(Constraint("linux2"), Constraint("darwin")))
    assert c.allows_all(Constraint("win32"))
    assert not c.allows_all(Constraint("darwin"))

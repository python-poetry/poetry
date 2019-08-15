from poetry.packages.constraints.constraint import Constraint
from poetry.packages.constraints.multi_constraint import MultiConstraint


def test_allows():
    c = MultiConstraint(Constraint("win32", "!="), Constraint("linux", "!="))

    assert not c.allows(Constraint("win32"))
    assert not c.allows(Constraint("linux"))
    assert c.allows(Constraint("darwin"))


def test_allows_any():
    c = MultiConstraint(Constraint("win32", "!="), Constraint("linux", "!="))

    assert c.allows_any(Constraint("darwin"))
    assert c.allows_any(Constraint("darwin", "!="))
    assert not c.allows_any(Constraint("win32"))
    assert c.allows_any(c)
    assert c.allows_any(
        MultiConstraint(Constraint("win32", "!="), Constraint("darwin", "!="))
    )


def test_allows_all():
    c = MultiConstraint(Constraint("win32", "!="), Constraint("linux", "!="))

    assert c.allows_all(Constraint("darwin"))
    assert c.allows_all(Constraint("darwin", "!="))
    assert not c.allows_all(Constraint("win32"))
    assert c.allows_all(c)
    assert not c.allows_all(
        MultiConstraint(Constraint("win32", "!="), Constraint("darwin", "!="))
    )


def test_intersect():
    c = MultiConstraint(Constraint("win32", "!="), Constraint("linux", "!="))

    intersection = c.intersect(Constraint("win32", "!="))
    assert intersection == Constraint("win32", "!=")

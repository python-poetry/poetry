from poetry.packages.constraints.constraint import Constraint
from poetry.packages.constraints.empty_constraint import EmptyConstraint
from poetry.packages.constraints.multi_constraint import MultiConstraint
from poetry.packages.constraints.union_constraint import UnionConstraint


def test_allows():
    c = Constraint("win32")

    assert c.allows(Constraint("win32"))
    assert not c.allows(Constraint("linux"))

    c = Constraint("win32", "!=")

    assert not c.allows(Constraint("win32"))
    assert c.allows(Constraint("linux"))


def test_allows_any():
    c = Constraint("win32")

    assert c.allows_any(Constraint("win32"))
    assert not c.allows_any(Constraint("linux"))
    assert c.allows_any(UnionConstraint(Constraint("win32"), Constraint("linux")))
    assert c.allows_any(Constraint("linux", "!="))

    c = Constraint("win32", "!=")

    assert not c.allows_any(Constraint("win32"))
    assert c.allows_any(Constraint("linux"))
    assert c.allows_any(UnionConstraint(Constraint("win32"), Constraint("linux")))
    assert c.allows_any(Constraint("linux", "!="))


def test_allows_all():
    c = Constraint("win32")

    assert c.allows_all(Constraint("win32"))
    assert not c.allows_all(Constraint("linux"))
    assert not c.allows_all(Constraint("linux", "!="))
    assert not c.allows_all(UnionConstraint(Constraint("win32"), Constraint("linux")))


def test_intersect():
    c = Constraint("win32")

    intersection = c.intersect(Constraint("linux"))
    assert intersection == EmptyConstraint()

    intersection = c.intersect(
        UnionConstraint(Constraint("win32"), Constraint("linux"))
    )
    assert intersection == Constraint("win32")

    intersection = c.intersect(
        UnionConstraint(Constraint("linux"), Constraint("linux2"))
    )
    assert intersection == EmptyConstraint()

    intersection = c.intersect(Constraint("linux", "!="))
    assert intersection == c

    c = Constraint("win32", "!=")

    intersection = c.intersect(Constraint("linux", "!="))
    assert intersection == MultiConstraint(
        Constraint("win32", "!="), Constraint("linux", "!=")
    )


def test_union():
    c = Constraint("win32")

    union = c.union(Constraint("linux"))
    assert union == UnionConstraint(Constraint("win32"), Constraint("linux"))

    union = c.union(UnionConstraint(Constraint("win32"), Constraint("linux")))
    assert union == UnionConstraint(Constraint("win32"), Constraint("linux"))

    union = c.union(UnionConstraint(Constraint("linux"), Constraint("linux2")))
    assert union == UnionConstraint(
        Constraint("win32"), Constraint("linux"), Constraint("linux2")
    )


def test_difference():
    c = Constraint("win32")

    assert c.difference(Constraint("win32")).is_empty()
    assert c.difference(Constraint("linux")) == c

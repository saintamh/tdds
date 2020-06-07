#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tdds
from tdds import Record, RecordsAreImmutable
from tdds.utils.compatibility import text_type

# this module
from .plumbing import assert_eq, assert_is, assert_matches, assert_raises, build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test('objects can be of a subclass of the declared type')
def _():
    class Parent(object):
        pass
    class Child(Parent):
        pass
    class MyRecord(Record):
        obj = Parent
    c = Child()
    r = MyRecord(c)
    assert_is(r.obj, c)

@test('record classes can be subclassed as normal')
def _():
    class Parent(Record):
        name = text_type
    class Child(Parent):
        def greet(self):
            return 'Hello, {}'.format(self.name)
    assert_eq(Child('Pearl').greet(), 'Hello, Pearl')

@test('non-record subclasses just need to pass up constructor kwargs')
def _():
    class Parent(Record):
        name = text_type
        animate = bool
    class Child(Parent):
        def __init__(self, name):
            super(Child, self).__init__(
                name=name,
                animate=True,
            )
    pearl = Child('Pearl')
    assert_eq(pearl.name, 'Pearl')
    assert_is(pearl.animate, True)

@test('non-record subclasses are still immutable, though')
def _():
    class Parent(Record):
        name = text_type
        animate = bool
    class Child(Parent):
        def __init__(self, name, favourite_color):
            self.favourite_color = favourite_color # <-- boom
            super(Child, self).__init__(
                name=name,
                animate=True,
            )
    with assert_raises(RecordsAreImmutable):
        Child('Pearl', 'red')

#----------------------------------------------------------------------------------------------------------------------------------

@test('if a non-record subclass defines its own __key__, it overrides the default one')
def _():
    class Point(Record):
        x = int
        y = int
    assert_eq(
        sorted([Point(0, 0), Point(0, 10), Point(10, 0), Point(10, 10)]),
        [Point(0, 0), Point(0, 10), Point(10, 0), Point(10, 10)],
    )
    class DownPoint(Point):
        def __key__(self):
            return (-self.y, -self.x)  # pylint: disable=invalid-unary-operand-type
    assert_eq(
        sorted([DownPoint(0, 0), DownPoint(0, 10), DownPoint(10, 0), DownPoint(10, 10)]),
        [DownPoint(10, 10), DownPoint(0, 10), DownPoint(10, 0), DownPoint(0, 0)],
    )

@test('if a non-record subclass defines its own __hash__, it overrides the default one')
def _():
    class Point(Record):
        x = int
        y = int
    class DownPoint(Point):
        def __hash__(self):
            return 1488451651
    assert_eq(
        hash(DownPoint(5, 5)),
        1488451651,
    )

@test('if a non-record subclass defines its own __repr__, it overrides the default one')
def _():
    class Point(Record):
        x = int
        y = int
    class DownPoint(Point):
        def __repr__(self):
            return '{%d--%d}' % (self.x, self.y)
    assert_eq(
        repr(DownPoint(13, 7)),
        '{13--7}',
    )

#----------------------------------------------------------------------------------------------------------------------------------

@test("if a record subclasses another, the subclass's record_fields contain fields from both")
def _():
    class Parent(Record):
        x = int
    class Child(Parent, Record):
        y = int
    assert_eq(
        sorted(Child.record_fields.keys()),
        ['x', 'y'],
    )

@test("if a record subclasses another, the subclass's __repr__ contains fields from both")
def _():
    class Parent(Record):
        x = int
    class Child(Parent, Record):
        y = int
    c = Child(x=5, y=9)
    assert_matches(r'\bx=5\b', repr(c))
    assert_matches(r'\by=9\b', repr(c))

@test("if a record subclasses another, the subclass's __hash__ uses fields from both")
def _():
    hashed = []
    class LoudHashable(object):
        def __init__(self, value):
            self.value = value
        def __hash__(self):
            hashed.append(self.value)
            return hash(self.value)
    class Parent(Record):
        x = LoudHashable
    class Child(Parent, Record):
        y = LoudHashable
    c = Child(x=LoudHashable(5), y=LoudHashable(9))
    hash(c)
    assert_eq(hashed, [5, 9])

# @test("if a record subclasses another, the subclass's __key__ uses fields from both")
# def _():
#     compared = []
#     class LoudComparable(object):
#         def __init__(self, value):
#             self.value = value
#         def __key__(self):
#             compared.append(self.value)
#             return (self.value,)
#     class Parent(Record):
#         x = LoudComparable
#     class Child(Parent, Record):
#         y = LoudComparable
#     c1 = Child(x=LoudComparable(5), y=LoudComparable(9))
#     c2 = Child(x=LoudComparable(5), y=LoudComparable(8))
#     _ = (c1 < c2)
#     assert_eq(compared, [5, 5), (9, 8)])

@test("if a record subclasses another, the subclass's record_pods includes fields from both")
def _():
    class Parent(Record):
        x = int
    class Child(Parent, Record):
        y = int
    c = Child(x=5, y=9)
    assert_eq(
        c.record_pods(),
        {'x': 5, 'y': 9},
    )

@test("if a record subclasses another, it cannot override the superclass's fields as that would invalidate superclass invariants")
def _():
    class Parent(Record):
        x = int
    with assert_raises(TypeError):
        class Child(Parent, Record):  # pylint: disable=unused-variable
            x = int

@test("if a record subclasses another, it cannot override the superclass's fields, even with a method")
def _():
    class Parent(Record):
        x = int
    with assert_raises(TypeError):
        class Child(Parent, Record):  # pylint: disable=unused-variable
            def x(self):
                pass

@test("if a record subclasses another, it cannot override the superclass's fields, even with a property")
def _():
    class Parent(Record):
        x = int
    with assert_raises(TypeError):
        class Child(Parent, Record):  # pylint: disable=unused-variable
            x = property(lambda self: 'ex')

@test("if a record subclasses another, it cannot override the superclass's fields, even with a classmethod")
def _():
    class Parent(Record):
        x = int
    with assert_raises(TypeError):
        class Child(Parent, Record):  # pylint: disable=unused-variable
            @classmethod
            def x(cls):
                pass

@test("if a record subclasses another, it cannot override the superclass's fields, even with a staticmethod")
def _():
    class Parent(Record):
        x = int
    with assert_raises(TypeError):
        class Child(Parent, Record):  # pylint: disable=unused-variable
            @staticmethod
            def x():
                pass

@test('if a record subclasses another, record_derive still works')
def _():
    class Parent(Record):
        x = int
    class Child(Parent, Record):
        y = int
    c = Child(1, 2)
    assert_eq(c.record_derive(x=3), Child(3, 2))
    assert_eq(c.record_derive(y=4), Child(1, 4))

# 2017-03-03 - I'm comment this one out even though it passes, but 3-way inheritance doesn't work anyway because of some problem
# with __slots__ (see 'Layout Conflicts' at http://mcjeff.blogspot.co.uk/2009/05/odd-python-errors.html)
#
# @test("can't subclass two record classes with a field having the same name, as I don't see how that could work")
# def _():
#     class LeftParent(Record):
#         x = int
#     class RightParent(Record):
#         x = int
#     with assert_raises(TypeError):
#         class Child(LeftParent, RightParent, Record):
#             y = int

#----------------------------------------------------------------------------------------------------------------------------------

# TODO make sure reduce works when pickling

#----------------------------------------------------------------------------------------------------------------------------------

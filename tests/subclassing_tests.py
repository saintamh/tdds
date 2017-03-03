#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# this module
from .. import *
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test("objects can be of a subclass of the declared type")
def _():
    class Parent (object):
        pass
    class Child (Parent):
        pass
    class R (Record):
        obj = Parent
    c = Child()
    r = R(c)
    assert_is (r.obj, c)

@test("record classes can be subclassed as normal")
def _():
    class Parent (Record):
        name = unicode
    class Child (Parent):
        def greet(self):
            return 'Hello, {}'.format(self.name)
    assert_eq(Child(u'Pearl').greet(), u'Hello, Pearl')

@test("non-record subclasses just need to pass up constructor kwards")
def _():
    class Parent (Record):
        name = unicode
        animate = bool
    class Child (Parent):
        def __init__(self, name):
            super(Child,self).__init__(
                name = name,
                animate = True,
            )
    pearl = Child(u'Pearl')
    assert_eq(pearl.name, u'Pearl')
    assert_is(pearl.animate, True)

@test("non-record subclasses are still immutable, though")
def _():
    class Parent (Record):
        name = unicode
        animate = bool
    class Child (Parent):
        def __init__(self, name, favourite_color):
            self.favourite_color = favourite_color # <-- boom
            super(Child,self).__init__(
                name = name,
                animate = True,
            )
    with expected_error(RecordsAreImmutable):
        Child(u'Pearl', 'red')

#----------------------------------------------------------------------------------------------------------------------------------

@test("if a non-record subclass defines its own __cmp__, it overrides the default one")
def _():
    class Point (Record):
        x = int
        y = int
    assert_eq(
        sorted([Point(0,0), Point(0,10), Point(10,0), Point(10,10)]),
        [Point(0,0), Point(0,10), Point(10,0), Point(10,10)],
    )
    class DownPoint (Point):
        def __cmp__ (self, other):
            return -cmp(self.y, other.y) or -cmp(self.x, other.x)
    assert_eq(
        sorted([DownPoint(0,0), DownPoint(0,10), DownPoint(10,0), DownPoint(10,10)]),
        [DownPoint(10,10), DownPoint(0,10), DownPoint(10,0), DownPoint(0,0)],
    )

@test("if a non-record subclass defines its own __hash__, it overrides the default one")
def _():
    class Point (Record):
        x = int
        y = int
    class DownPoint (Point):
        def __hash__ (self):
            return 1488451651
    assert_eq(
        hash(DownPoint(5,5)),
        1488451651,
    )

@test("if a non-record subclass defines its own __repr__, it overrides the default one")
def _():
    class Point (Record):
        x = int
        y = int
    class DownPoint (Point):
        def __repr__ (self):
            return '{%d--%d}' % (self.x, self.y)
    assert_eq(
        repr(DownPoint(13,7)),
        '{13--7}',
    )

#----------------------------------------------------------------------------------------------------------------------------------

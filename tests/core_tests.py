#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from abc import ABCMeta
from random import randrange

# record
from record import *
from record.utils.compatibility import integer_types, native_string, string_types, text_type

# this module
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# core core

@test('records are immutable')
def _():
    class R(Record):
        id = int
    r = R(10)
    with expected_error(RecordsAreImmutable):
        r.id = 11

#----------------------------------------------------------------------------------------------------------------------------------
# scalar fields

SCALAR_TYPES = string_types + integer_types + (float, bool)

@foreach(SCALAR_TYPES)
def val_type_tests(val_type):
    val_type_name = val_type.__name__

    @test("non-nullable {} fields can't be None".format(val_type_name))
    def _():
        class R(Record):
            id = val_type
        with expected_error(FieldNotNullable):
            R(id=None)

    @test("non-nullable {} fields can be zero".format(val_type_name))
    def _():
        class R(Record):
            id = val_type
        v = val_type(0)
        r = R(id=v)
        assert_eq(r.id, v)

    @test("nullable {} fields can be None".format(val_type_name))
    def _():
        class R(Record):
            id = nullable(val_type)
        r = R(id=None)
        assert_none(r.id)

    @test("{} fields can be defined with just the type".format(val_type_name))
    def _():
        class R(Record):
            id = val_type
        r = R(id=val_type(1))

    @test("{} fields defined with just the type are not nullable".format(val_type_name))
    def _():
        class R(Record):
            id = val_type
        with expected_error(FieldNotNullable):
            R(id=None)

#----------------------------------------------------------------------------------------------------------------------------------
# explicit Field defs

@test("fields can be defined using the Field class")
def _():
    class R(Record):
        id = Field(int)
    assert_eq(R(10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# properties

@test("you can set properties on a record class")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    assert_eq(r.square, 9)

@test("you can set properties (using a decorator) on a record class")
def _():
    class R(Record):
        x = int
        @property
        def square(self):
            return self.x*self.x
    r = R(3)
    assert_eq(r.square, 9)

@test("the property is set on the class itself, not its instances")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    assert_is(R.square.__class__, property)

@test("the property function it not internally cached, it gets invoked on every call") # unlike in struct.py
def _():
    returned = []
    def getnext(self):
        returned.append(len(returned))
        return returned[-1]
    class R(Record):
        x = int
        next_value = property(getnext)
    r = R(999)
    assert_eq(r.next_value, 0)
    assert_eq(r.next_value, 1)
    assert_eq(r.next_value, 2)
    assert_eq(len(returned), 3)

@test("properties cannot have an fset function")
def _():
    def fset_x(self, value):
        self.x = value
    square_prop = property(
        lambda self: self.x*self.x,
        fset_x,
    )
    with expected_error(TypeError):
        class R(Record):
            x = int
            square = square_prop

@test("properties cannot have an fdel function")
def _():
    def fdel_x(self):
        del self.x
    square_prop = property(
        lambda self: self.x*self.x,
        fdel = fdel_x,
    )
    with expected_error(TypeError):
        class R(Record):
            x = int
            square = square_prop

@test("cannot override a property by setting a value")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    with expected_error(RecordsAreImmutable):
        r.square = 18

@test("cannot override a property with a new one either")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    with expected_error(RecordsAreImmutable):
        r.square = property(lambda self: self.x**3)

@test("the property is not part of the record's fields")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    assert_eq(list(R.record_fields.keys()), ['x'])

@test("the property cannot be passed in to the constructor")
def _():
    class R(Record):
        x = int
        square = property(lambda self: self.x*self.x)
    with expected_error(TypeError):
        R(x=10, square=99)

#----------------------------------------------------------------------------------------------------------------------------------
# classmethods

@test("you can set classmethods on a record class")
def _():
    class R(Record):
        x = int
        parse = classmethod(lambda cls, value: cls(int(value)))
    r = R.parse('9')
    assert_eq(r.x, 9)

@test("you can set classmethods (using a decorator) on a record class")
def _():
    class R(Record):
        x = int
        @classmethod
        def parse(cls, value):
            return cls(int(value))
    r = R.parse('9')
    assert_eq(r.x, 9)

@test("the classmethod is not part of the record's fields")
def _():
    class R(Record):
        x = int
        parse = classmethod(lambda cls, value: cls(int(value)))
    assert_eq(list(R.record_fields.keys()), ['x'])

@test("the classmethod cannot be passed in to the constructor")
def _():
    class R(Record):
        x = int
        parse = classmethod(lambda cls, value: cls(int(value)))
    with expected_error(TypeError):
        R(x=10, parse='blah')

#----------------------------------------------------------------------------------------------------------------------------------
# staticmethods

@test("you can set staticmethods on a record class")
def _():
    class R(Record):
        x = int
        square = staticmethod(lambda value: value*value)
    r = R(3)
    assert_eq(R.square(9), 81)

@test("you can set staticmethods (using a decorator) on a record class")
def _():
    class R(Record):
        x = int
        @staticmethod
        def square(value):
            return value*value
    r = R(3)
    assert_eq(R.square(9), 81)

@test("the staticmethod is not part of the record's fields")
def _():
    class R(Record):
        x = int
        square = staticmethod(lambda value: value*value)
    assert_eq(list(R.record_fields.keys()), ['x'])

@test("the staticmethod cannot be passed in to the constructor")
def _():
    class R(Record):
        x = int
        square = staticmethod(lambda value: value*value)
    with expected_error(TypeError):
        R(x=10, square='blah')

#----------------------------------------------------------------------------------------------------------------------------------
# overriding standard methods

@test("classes have a default text representation")
def _():
    class Point(Record):
        x = int
        y = int
    assert_eq(
        text_type(Point(5, 6)),
        'Point(x=5, y=6)',
    )

@test("classes can set their own __str__")
def _():
    class Point(Record):
        x = int
        y = int
        def __str__(self):
            return '[%d,%d]' % (self.x, self.y)
    assert_eq(
        text_type(Point(5, 6)),
        '[5,6]',
    )

@test("classes have a default __repr__")
def _():
    class Point(Record):
        x = int
        y = int
    assert_eq(
        repr(Point(5, 6)),
        'Point(x=5, y=6)',
    )

@test("classes can set their own __repr__")
def _():
    class Point(Record):
        x = int
        y = int
        def __repr__(self):
            return 'Point(%d,%d)' % (self.x, self.y)
    assert_eq(
        repr(Point(5, 6)),
        'Point(5,6)',
    )

@test("classes have a default sort order, which sorts by alphabetical field name")
def _():
    class Name(Record):
        first = text_type
        middle = text_type
        last = text_type
    assert_eq(
        sorted((
            Name(first="Jesus", middle="H.", last="Christ"),
            Name(first="Jesus", middle="de", last="Nazareth"),
            Name(first="King", middle="of", last="Jews"),
        )),
        [
            # 'last' comes before 'middle'
            Name(first="Jesus", middle="H.", last="Christ"),
            Name(first="Jesus", middle="de", last="Nazareth"),
            Name(first="King", middle="of", last="Jews"),
        ]
    )

@test("classes can define their own __key__, which impacts the sort order")
def _():
    class Name(Record):
        first = text_type
        middle = text_type
        last = text_type
        def __key__(self):
            return (self.last, self.first, self.middle)
    assert_eq(
        sorted((
            Name(first="Jesus", middle="H.", last="Christ"),
            Name(first="Jesus", middle="de", last="Nazareth"),
            Name(first="King", middle="of", last="Jews"),
        )),
        [
            Name(first="Jesus", middle="H.", last="Christ"),
            Name(first="King", middle="of", last="Jews"),
            Name(first="Jesus", middle="de", last="Nazareth"),
        ]
    )

@test("classes have a default __hash__")
def _():
    class Point(Record):
        x = int
        y = int
    for _ in range(1000):
        x = randrange(1000)
        y = randrange(1000)
        assert_eq(
            hash(Point(x, y)),
            hash(Point(x, y)),
        )

@test("classes can define their own __hash__")
def _():
    hash_impl = max
    class Point(Record):
        x = int
        y = int
        def __hash__(self):
            return hash_impl(self.x, self.y)
    for _ in range(1000):
        x = randrange(1000)
        y = randrange(1000)
        assert_eq(
            hash(Point(x, y)),
            hash_impl(x, y),
        )

@test("the default __hash__ uses __key__")
def _():
    class Point(Record):
        x = int
        y = int
        def __key__(self):
            return (self.x,)
    for _ in range(1000):
        x = randrange(1000)
        assert_eq(
            hash(Point(x, randrange(1000))),
            hash(Point(x, randrange(1000))),
        )

#----------------------------------------------------------------------------------------------------------------------------------
# abc's

@test("type tests allow using ABC's")
def _():
    MyType = ABCMeta(
        native_string('MyType'),
        (object,),
        {},
    )
    MyType.register(int)
    class R(Record):
        value = MyType
    assert_eq(
        R(value=42).value,
        42,
    )

#----------------------------------------------------------------------------------------------------------------------------------

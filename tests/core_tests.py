#!/usr/bin/env python
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
# core core

@test('records are immutable')
def _():
    class R (Record):
        id = int
    r = R(10)
    with expected_error(RecordsAreImmutable):
        r.id = 11

#----------------------------------------------------------------------------------------------------------------------------------
# scalar fields

SCALAR_TYPES = (int,long,float,str,unicode)

@foreach(SCALAR_TYPES)
def val_type_tests (val_type):
    val_type_name = val_type.__name__

    @test("non-nullable {} fields can't be None".format(val_type_name))
    def _():
        class R (Record):
            id = val_type
        with expected_error(FieldNotNullable):
            R(id=None)

    @test("non-nullable {} fields can be zero".format(val_type_name))
    def _():
        class R (Record):
            id = val_type
        v = val_type(0)
        r = R(id=v)
        assert_eq (r.id, v)

    @test("nullable {} fields can be None".format(val_type_name))
    def _():
        class R (Record):
            id = nullable(val_type)
        r = R(id=None)
        assert_none (r.id)

    @test("{} fields can be defined with just the type".format(val_type_name))
    def _():
        class R (Record):
            id = val_type
        r = R(id=val_type(1))

    @test("{} fields defined with just the type are not nullable".format(val_type_name))
    def _():
        class R (Record):
            id = val_type
        with expected_error(FieldNotNullable):
            R(id=None)

#----------------------------------------------------------------------------------------------------------------------------------
# explicit Field defs

@test("fields can be defined using the Field class")
def _():
    class R (Record):
        id = Field(int)
    assert_eq (R(10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# more type checks

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

@test("record classes can be subclasses as normal")
def _():
    class R (Record):
        name = unicode
    class Person (R):
        def greet(self):
            return 'Hello, {}'.format(self.name)
    assert_eq(Person(u'Pearl').greet(), u'Hello, Pearl')

#----------------------------------------------------------------------------------------------------------------------------------
# properties

@test("you can set properties on a record class")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    assert_eq (r.square, 9)

@test("you can set properties (using a decorator) on a record class")
def _():
    class R (Record):
        x = int
        @property
        def square(self):
            return self.x*self.x
    r = R(3)
    assert_eq (r.square, 9)

@test("the property is set on the class itself, not its instances")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    assert_is (R.square.__class__, property)

@test("the property function it not internally cached, it gets invoked on every call") # unlike in struct.py
def _():
    returned = []
    def getnext(self):
        returned.append(len(returned))
        return returned[-1]
    class R (Record):
        x = int
        next_value = property(getnext)
    r = R(999)
    assert_eq (r.next_value, 0)
    assert_eq (r.next_value, 1)
    assert_eq (r.next_value, 2)
    assert_eq (len(returned), 3)

@test("properties cannot have an fset function")
def _():
    def fset_x(self, val):
        self.x = val
    square_prop = property (
        lambda self: self.x*self.x,
        fset_x,
    )
    with expected_error(TypeError):
        record ('R', x=int, square=square_prop)

@test("properties cannot have an fdel function")
def _():
    def fdel_x(self):
        del self.x
    square_prop = property (
        lambda self: self.x*self.x,
        fdel = fdel_x,
    )
    with expected_error(TypeError):
        record ('R', x=int, square=square_prop)

@test("cannot override a property by setting a value")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    with expected_error(RecordsAreImmutable):
        r.square = 18

@test("cannot override a property with a new one either")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    r = R(3)
    with expected_error(RecordsAreImmutable):
        r.square = property(lambda self: self.x**3)

@test("the property is not part of the record's fields")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    assert_eq(R.record_fields.keys(), ['x'])

@test("the property cannot be passed in to the constructor")
def _():
    class R (Record):
        x = int
        square = property(lambda self: self.x*self.x)
    with expected_error(TypeError):
        R(x=10, square=99)

#----------------------------------------------------------------------------------------------------------------------------------
# classmethods

@test("you can set classmethods on a record class")
def _():
    class R (Record):
        x = int
        parse = classmethod(lambda cls, val: cls(int(val)))
    r = R.parse('9')
    assert_eq (r.x, 9)

@test("you can set classmethods (using a decorator) on a record class")
def _():
    class R (Record):
        x = int
        @classmethod
        def parse(cls, val):
            return cls(int(val))
    r = R.parse('9')
    assert_eq (r.x, 9)

@test("the classmethod is not part of the record's fields")
def _():
    class R (Record):
        x = int
        parse = classmethod(lambda cls, val: cls(int(val)))
    assert_eq(R.record_fields.keys(), ['x'])

@test("the classmethod cannot be passed in to the constructor")
def _():
    class R (Record):
        x = int
        parse = classmethod(lambda cls, val: cls(int(val)))
    with expected_error(TypeError):
        R(x=10, parse='blah')

#----------------------------------------------------------------------------------------------------------------------------------
# staticmethods

@test("you can set staticmethods on a record class")
def _():
    class R (Record):
        x = int
        square = staticmethod(lambda val: val*val)
    r = R(3)
    assert_eq (R.square(9), 81)

@test("you can set staticmethods (using a decorator) on a record class")
def _():
    class R (Record):
        x = int
        @staticmethod
        def square(val):
            return val*val
    r = R(3)
    assert_eq (R.square(9), 81)

@test("the staticmethod is not part of the record's fields")
def _():
    class R (Record):
        x = int
        square = staticmethod(lambda val: val*val)
    assert_eq(R.record_fields.keys(), ['x'])

@test("the staticmethod cannot be passed in to the constructor")
def _():
    class R (Record):
        x = int
        square = staticmethod(lambda val: val*val)
    with expected_error(TypeError):
        R(x=10, square='blah')

#----------------------------------------------------------------------------------------------------------------------------------

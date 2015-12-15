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

@test('records are immutable')
def _():
    R = record ('R', id = int)
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
        R = record ('R', id=val_type)
        with expected_error(FieldNotNullable):
            R(id=None)

    @test("non-nullable {} fields can be zero".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        v = val_type(0)
        r = R(id=v)
        assert_eq (r.id, v)

    @test("nullable {} fields can be None".format(val_type_name))
    def _():
        R = record ('R', id=nullable(val_type))
        r = R(id=None)
        assert_none (r.id)

    @test("{} fields can be defined with just the type".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        r = R(id=val_type(1))

    @test("{} fields defined with just the type are not nullable".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        with expected_error(FieldNotNullable):
            R(id=None)

#----------------------------------------------------------------------------------------------------------------------------------
# explicit Field defs

@test("fields can be defined using the Field class")
def _():
    R = record ('R', id=Field(int))
    assert_eq (R(10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# more type checks

@test("objects can be of a subclass of the declared type")
def _():
    class Parent (object):
        pass
    class Child (Parent):
        pass
    R = record ('R', obj=Parent)
    c = Child()
    r = R(c)
    assert_is (r.obj, c)

#----------------------------------------------------------------------------------------------------------------------------------

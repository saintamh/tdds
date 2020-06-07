#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tdds
from tdds import FieldTypeError, Record, RecursiveType, nullable, dict_of, pair_of, seq_of, set_of
from tdds.utils.compatibility import text_type

# this module
from .plumbing import assert_eq, assert_is, assert_raises, build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test('RecursiveType allows recursive type definitions')
def _():
    class MyRecord(Record):
        nxt = nullable(RecursiveType)
    r1 = MyRecord()
    r2 = MyRecord(r1)
    assert_is(r2.nxt, r1)

@test("RecursiveType doesn't allow other types")
def _():
    class MyRecord(Record):
        nxt = nullable(RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord('something else')

@test('RecursiveType works with subtypes')
def _():
    class MyRecord(Record):
        nxt = nullable(RecursiveType)
    SubR = type(str('SubR'), (MyRecord,), {}) # NB name is native string in PY2+3
    r1 = SubR()
    r2 = MyRecord(r1)
    assert_is(r2.nxt, r1)

#----------------------------------------------------------------------------------------------------------------------------------
# PODS

@test('Recursive types can be serialized to PODS')
def _():
    class MyRecord(Record):
        nxt = nullable(RecursiveType)
    d = MyRecord(MyRecord()).record_pods()
    assert_eq(d, {'nxt': {}})

@test('Recursive types can be decoded from PODS')
def _():
    class MyRecord(Record):
        nxt = nullable(RecursiveType)
    r = MyRecord.from_pods({'nxt': {}})
    assert_eq(r, MyRecord(MyRecord()))

#----------------------------------------------------------------------------------------------------------------------------------
# collections

@test('RecursiveType works with sequences')
def _():
    class MyRecord(Record):
        children = seq_of(RecursiveType)
    r1 = MyRecord([])
    r2 = MyRecord([r1])
    assert_is(r2.children[0], r1)  # you're confused, pylint: disable=unsubscriptable-object

@test("RecursiveType doesn't allow sequence elems with other types")
def _():
    class MyRecord(Record):
        children = seq_of(RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord(['something else'])

@test('RecursiveType works with pairs')
def _():
    class MyRecord(Record):
        children = nullable(pair_of(RecursiveType))
    r1 = MyRecord()
    r2 = MyRecord()
    r3 = MyRecord([r1, r2])
    assert_is(r3.children[0], r1)

@test("RecursiveType doesn't allow pair elems with other types")
def _():
    class MyRecord(Record):
        children = pair_of(RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord(['something', 'else'])

@test('RecursiveType works with sets')
def _():
    class MyRecord(Record):
        children = set_of(RecursiveType)
    r1 = MyRecord([])
    r2 = MyRecord([r1])
    assert_is(next(iter(r2.children)), r1)

@test("RecursiveType doesn't allow set elems with other types")
def _():
    class MyRecord(Record):
        children = set_of(RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord(['something else'])

@test('RecursiveType works with dict keys')
def _():
    class MyRecord(Record):
        children = dict_of(RecursiveType, text_type)
    r1 = MyRecord([])
    r2 = MyRecord({r1: '1'})
    assert_is(next(iter(r2.children)), r1)

@test("RecursiveType doesn't allow set dict keys with other types")
def _():
    class MyRecord(Record):
        children = dict_of(text_type, RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord({'1': 'one'})

@test('RecursiveType works with dict values')
def _():
    class MyRecord(Record):
        children = dict_of(text_type, RecursiveType)
    r1 = MyRecord([])
    r2 = MyRecord({'1': r1})
    assert_is(r2.children['1'], r1)  # you're confused, pylint: disable=unsubscriptable-object

@test("RecursiveType doesn't allow set dict values with other types")
def _():
    class MyRecord(Record):
        children = dict_of(text_type, RecursiveType)
    with assert_raises(FieldTypeError):
        MyRecord({'1': 'something else'})

#----------------------------------------------------------------------------------------------------------------------------------

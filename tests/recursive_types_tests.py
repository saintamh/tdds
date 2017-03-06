#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
$Id: $
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

@test("RecursiveType allows recursive type definitions")
def _():
    class R(Record):
        nxt = nullable(RecursiveType)
    r1 = R()
    r2 = R(r1)
    assert_is(r2.nxt, r1)

@test("RecursiveType doesn't allow other types")
def _():
    class R(Record):
        nxt = nullable(RecursiveType)
    with expected_error(FieldTypeError):
        R("something else")

@test("RecursiveType works with subtypes")
def _():
    class R(Record):
        nxt = nullable(RecursiveType)
    SubR = type('SubR', (R,), {})
    r1 = SubR()
    r2 = R(r1)
    assert_is(r2.nxt, r1)

#----------------------------------------------------------------------------------------------------------------------------------
# PODS

@test("Recursive types can be serialized to PODS")
def _():
    class R(Record):
        nxt = nullable(RecursiveType)
    d = R(R()).record_pods()
    assert_eq(d, {"nxt": {}})

@test("Recursive types can be decoded from PODS")
def _():
    class R(Record):
        nxt = nullable(RecursiveType)
    r = R.from_pods({"nxt": {}})
    assert_eq(r, R(R()))

#----------------------------------------------------------------------------------------------------------------------------------
# collections

@test("RecursiveType works with sequences")
def _():
    class R (Record):
        children = seq_of(RecursiveType)
    r1 = R([])
    r2 = R([r1])
    assert_is (r2.children[0], r1)

@test("RecursiveType doesn't allow sequence elems with other types")
def _():
    class R (Record):
        children = seq_of(RecursiveType)
    with expected_error(FieldTypeError):
        R(["something else"])

@test("RecursiveType works with pairs")
def _():
    class R (Record):
        children = nullable(pair_of(RecursiveType))
    r1 = R()
    r2 = R()
    r3 = R([r1, r2])
    assert_is (r3.children[0], r1)

@test("RecursiveType doesn't allow pair elems with other types")
def _():
    class R (Record):
        children = pair_of(RecursiveType)
    with expected_error(FieldTypeError):
        R(["something", "else"])

@test("RecursiveType works with sets")
def _():
    class R (Record):
        children = set_of(RecursiveType)
    r1 = R([])
    r2 = R([r1])
    assert_is (iter(r2.children).next(), r1)

@test("RecursiveType doesn't allow set elems with other types")
def _():
    class R (Record):
        children = set_of(RecursiveType)
    with expected_error(FieldTypeError):
        R(["something else"])

@test("RecursiveType works with dict keys")
def _():
    class R (Record):
        children = dict_of(RecursiveType, str)
    r1 = R([])
    r2 = R({r1: '1'})
    assert_is (iter(r2.children).next(), r1)

@test("RecursiveType doesn't allow set dict keys with other types")
def _():
    class R (Record):
        children = dict_of(str, RecursiveType)
    with expected_error(FieldTypeError):
        R({'1': "one"})

@test("RecursiveType works with dict values")
def _():
    class R (Record):
        children = dict_of(str, RecursiveType)
    r1 = R([])
    r2 = R({'1': r1})
    assert_is (r2.children['1'], r1)

@test("RecursiveType doesn't allow set dict values with other types")
def _():
    class R (Record):
        children = dict_of(str, RecursiveType)
    with expected_error(FieldTypeError):
        R({'1': "something else"})

#----------------------------------------------------------------------------------------------------------------------------------

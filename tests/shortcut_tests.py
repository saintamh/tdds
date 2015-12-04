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
# number utils

@test("nonnegative numbers cannot be smaller than zero")
def _():
    R = record ('R', id=nonnegative(int))
    with expected_error(FieldValueError):
        R(id=-1)

@test("nonnegative numbers can be zero")
def _():
    R = record ('R', id=nonnegative(int))
    assert_eq (R(id=0).id, 0)

@test("nonnegative numbers can be greater than zero")
def _():
    R = record ('R', id=nonnegative(int))
    assert_eq (R(id=10).id, 10)

@test("strictly_positive numbers cannot be smaller than zero")
def _():
    R = record ('R', id=strictly_positive(int))
    with expected_error(FieldValueError):
        R(id=-1)

@test("strictly_positive numbers cannot be zero")
def _():
    R = record ('R', id=strictly_positive(int))
    with expected_error(FieldValueError):
        R(id=0)

@test("strictly_positive numbers can be greater than zero")
def _():
    R = record ('R', id=strictly_positive(int))
    assert_eq (R(id=10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# string utils

@test("uppercase_letters(3) accepts 3 uppercase letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    assert_eq (R(s='ABC').s, 'ABC')

@test("uppercase_letters(3) doesn't accept less than 3 letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldValueError):
        R(s='AB')

@test("uppercase_letters(3) doesn't accept more than 3 letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldValueError):
        R(s='ABCD')

@test("uppercase_letters doesn't accept lowercase letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldValueError):
        R(s='abc')

@test("uppercase_letters() accepts any number of uppercase letters")
def _():
    R = record ('R', s=uppercase_letters())
    assert_eq (R(s='ABCDEFGH').s, 'ABCDEFGH')

@test("uppercase_letters() accepts empty strings")
def _():
    R = record ('R', s=uppercase_letters())
    assert_eq (R(s='').s, '')

@test("uppercase_letters() still only accepts uppercase letters")
def _():
    R = record ('R', s=uppercase_letters())
    with expected_error(FieldValueError):
        R(s='a')

#----------------------------------------------------------------------------------------------------------------------------------
# one_of

@test("one_of accepts a fixed list of values")
def _():
    R = record ('R', v=one_of('a','b','c'))
    assert_eq (R(v='a').v, 'a')

@test("one_of doesn't accept values outside the given list")
def _():
    R = record ('R', v=one_of('a','b','c'))
    with expected_error(FieldValueError):
        R(v='d')

@test("one_of does not accept an empty argument list")
def _():
    with expected_error(ValueError):
        one_of()

@test("all arguments to one_of must have the same type")
def _():
    with expected_error(ValueError):
        one_of ('a',object())
    
@test("one_of compares values based on == rather than `is'")
def _():
    class C (object):
        def __init__ (self, value):
            self.value = value
        def __cmp__ (self, other):
            return cmp (self.value[0], other.value[0])
        def __hash__ (self):
            return hash(self.value[0])
    c1 = C (['a','bcde'])
    c2 = C (['a','bracadabra'])
    R = record ('R', c=one_of(c1))
    assert_eq (R(c=c2).c, c2)

#----------------------------------------------------------------------------------------------------------------------------------
# nonempty

def define_nonempty_tests (ftype, ftype_name, empty_val):

    @test("in general {} fields can be empty".format(ftype_name))
    def _():
        R = record ('R', v=ftype)
        assert_eq (len(R(empty_val).v), 0)

    @test("nonempty {} can't be empty".format(ftype_name))
    def _():
        R = record ('R', v=nonempty(ftype))
        with expected_error (FieldValueError):
            R(empty_val)

for ftype,ftype_name,empty_val in (
        (str, "str's", ''),
        (unicode, 'unicode strings', u''),
        (seq_of(int), 'seqeuence fields', ()),
        (set_of(int), 'set fields', ()),
        (dict_of(int,int), 'dict fields', {}),
        ):
    define_nonempty_tests (ftype, ftype_name, empty_val)

#----------------------------------------------------------------------------------------------------------------------------------

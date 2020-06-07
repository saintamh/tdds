#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import total_ordering

# tdds
from tdds import (
    FieldValueError,
    Record,
    dict_of,
    one_of,
    nonempty,
    nonnegative,
    nullable,
    seq_of,
    set_of,
    strictly_positive,
    uppercase_letters,
    uppercase_wchars,
)
from tdds.utils.compatibility import bytes_type, text_type

# this module
from .plumbing import assert_eq, assert_none, assert_raises, build_test_registry, foreach

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# number utils

@test('nonnegative numbers cannot be smaller than zero')
def _():
    class MyRecord(Record):
        id = nonnegative(int)
    with assert_raises(FieldValueError):
        MyRecord(id=-1)

@test('nonnegative numbers can be zero')
def _():
    class MyRecord(Record):
        id = nonnegative(int)
    assert_eq(MyRecord(id=0).id, 0)

@test('nonnegative numbers can be greater than zero')
def _():
    class MyRecord(Record):
        id = nonnegative(int)
    assert_eq(MyRecord(id=10).id, 10)

@test('strictly_positive numbers cannot be smaller than zero')
def _():
    class MyRecord(Record):
        id = strictly_positive(int)
    with assert_raises(FieldValueError):
        MyRecord(id=-1)

@test('strictly_positive numbers cannot be zero')
def _():
    class MyRecord(Record):
        id = strictly_positive(int)
    with assert_raises(FieldValueError):
        MyRecord(id=0)

@test('strictly_positive numbers can be greater than zero')
def _():
    class MyRecord(Record):
        id = strictly_positive(int)
    assert_eq(MyRecord(id=10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# string utils

@test('uppercase_letters(3) accepts 3 uppercase letters')
def _():
    class MyRecord(Record):
        s = uppercase_letters(3)
    assert_eq(MyRecord(s='ABC').s, 'ABC')

@test("uppercase_letters(3) doesn't accept less than 3 letters")
def _():
    class MyRecord(Record):
        s = uppercase_letters(3)
    with assert_raises(FieldValueError):
        MyRecord(s='AB')

@test("uppercase_letters(3) doesn't accept more than 3 letters")
def _():
    class MyRecord(Record):
        s = uppercase_letters(3)
    with assert_raises(FieldValueError):
        MyRecord(s='ABCD')

@test("uppercase_letters doesn't accept lowercase letters")
def _():
    class MyRecord(Record):
        s = uppercase_letters(3)
    with assert_raises(FieldValueError):
        MyRecord(s='abc')

@test('uppercase_letters() accepts any number of uppercase letters')
def _():
    class MyRecord(Record):
        s = uppercase_letters()
    assert_eq(MyRecord(s='ABCDEFGH').s, 'ABCDEFGH')

@test('uppercase_letters() accepts empty strings')
def _():
    class MyRecord(Record):
        s = uppercase_letters()
    assert_eq(MyRecord(s='').s, '')

@test('uppercase_letters() still only accepts uppercase letters')
def _():
    class MyRecord(Record):
        s = uppercase_letters()
    with assert_raises(FieldValueError):
        MyRecord(s='a')

#----------------------------------------------------------------------------------------------------------------------------------
# one_of

@test('one_of accepts a fixed list of values')
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c')
    assert_eq(MyRecord(v='a').v, 'a')

@test("one_of doesn't accept values outside the given list")
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c')
    with assert_raises(FieldValueError):
        MyRecord(v='d')

@test('one_of does not accept an empty argument list')
def _():
    with assert_raises(ValueError):
        one_of()

@test('all arguments to one_of must have the same type')
def _():
    with assert_raises(ValueError):
        one_of('a', object())

@test("one_of compares values based on == rather than `is'")
def _():
    @total_ordering
    class MyClass(object):
        def __init__(self, value):
            self.value = value
        def __eq__(self, other):
            return self.value[0] == other.value[0]
        def __lt__(self, other):
            return self.value[0] < other.value[0]
        def __hash__(self):
            return hash(self.value[0])
    c1 = MyClass(['a', 'bcde'])
    c2 = MyClass(['a', 'bracadabra'])
    class MyRecord(Record):
        c = one_of(c1)
    assert_eq(MyRecord(c=c2).c, c2)

@test('one_of fields can be nullable')
def _():
    class MyRecord(Record):
        v = nullable(one_of('a', 'b', 'c'))
    assert_eq(MyRecord('a').v, 'a')
    assert_none(MyRecord(None).v)

@test('one_of fields can also be made nullable using a kwarg')
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c', nullable=True)
    assert_eq(MyRecord('a').v, 'a')
    assert_none(MyRecord(None).v)

@test('one_of accepts a `default` kwarg')
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c', nullable=True, default='b')
    assert_eq(MyRecord().v, 'b')
    assert_eq(MyRecord(None).v, 'b')

@test('the default needs to be in the whitelist')
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c', nullable=True, default='z')
    with assert_raises(FieldValueError, "MyRecord.v: 'z' is not a valid value"):
        assert_eq(MyRecord().v, 'b')

@test('one_of also accepts a `coerce` kwarg')
def _():
    class MyRecord(Record):
        v = one_of('a', 'b', 'c', coerce=text_type.lower)
    assert_eq(MyRecord('C').v, 'c')

#----------------------------------------------------------------------------------------------------------------------------------
# nonempty

@foreach((
    (bytes_type, 'byte strings', b''),
    (text_type, 'text strings', ''),
    (seq_of(int), 'seqeuence fields', ()),
    (set_of(int), 'set fields', ()),
    (dict_of(int, int), 'dict fields', {}),
))
def _(ftype, ftype_name, empty_val):

    @test('in general {} fields can be empty'.format(ftype_name))
    def _():
        class MyRecord(Record):
            v = ftype
        assert_eq(len(MyRecord(empty_val).v), 0)
    @test("nonempty {} can't be empty".format(ftype_name))
    def _():
        class MyRecord(Record):
            v = nonempty(ftype)
        with assert_raises(FieldValueError):
            MyRecord(empty_val)

#----------------------------------------------------------------------------------------------------------------------------------
# misc

@test('uppercase_wchars() fields can be nullable')
def _():
    # 2017-02-07 - I wrote half a year ago that this wasn't working. Wrote the test today, it passes. I'll leave it here although
    # it does seem redundant.
    class MyRecord(Record):
        s = nullable(uppercase_wchars(10))
    assert_none(MyRecord().s)

#----------------------------------------------------------------------------------------------------------------------------------

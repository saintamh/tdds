#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple
from datetime import datetime, timedelta
from decimal import Decimal

# tdds
from tdds import (
    CannotBeSerializedToPods,
    FieldNotNullable,
    Marshaller,
    Record,
    dict_of,
    nullable,
    pair_of,
    seq_of,
    set_of,
    temporary_marshaller_registration,
)
from tdds.utils.compatibility import bytes_type, integer_types, text_type

# this module
from .plumbing import assert_eq, assert_isinstance, assert_raises, build_test_registry, foreach

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# sanity

@test('scalar fields are directly rendered to a PODS')
def _():
    class MyRecord(Record):
        id = text_type
        label = text_type
        age = int
        salary = float
    r = MyRecord(id='robert', label='Robert Smith', age=42, salary=12.70)
    d = r.record_pods()
    assert_eq(d, {
        'id': 'robert',
        'label': 'Robert Smith',
        'age': 42,
        'salary': 12.70,
    })

@test('nested records are rendered to a PODS as nested objects')
def _():
    class Name(Record):
        first = text_type
        last = text_type
    class Person(Record):
        name = Name
        age = int
    p = Person(name=Name(first='Robert', last='Smith'), age=100)
    d = p.record_pods()
    assert_eq(d, {
        'name': {
            'first': 'Robert',
            'last': 'Smith',
        },
        'age': 100,
    })

#----------------------------------------------------------------------------------------------------------------------------------
# type-specific tests

def _other_record():
    class R2(Record):
        v = int
    return R2

@foreach(
    (class_name, cls, value, nullable_or_not)
    for class_name, cls, non_null_val in (
        ('bytes', bytes_type, b'\xE2\x9C\x93\'\\\"\xE2\x9C\x93'),
        ('text', text_type, 'Herv\u00E9\'\\\"Herv\u00E9'),
        ('ascii-only text', text_type, 'ASCII'),
    ) + tuple(
        (t.__name__, t, t(42))
        for t in integer_types
    ) + (
        ('float', float, 0.3),
        ('bool', bool, True),
        ('sequence (nonempty)', seq_of(int), (1, 2, 3)),
        ('sequence (empty)', seq_of(int), []),
        ('set (nonempty)', set_of(int), (1, 2, 3)),
        ('set (empty)', set_of(int), []),
        ('dict (nonempty)', dict_of(text_type, int), {'one':1, 'two':2}),
        ('dict (empty)', dict_of(text_type, int), []),
        ('datetime', datetime, datetime(2016, 4, 15, 10, 1, 59)),
        ('timedelta', timedelta, timedelta(days=1, hours=2, minutes=3, seconds=4)),
        (lambda R2: ('other record', R2, R2(2)))(_other_record()),
    )
    for nullable_or_not, vals in (
        (lambda f: f, (non_null_val,)),
        (nullable, (non_null_val, None)),
    )
    for value in vals
)
def _(class_name, cls, value, nullable_or_not):

    @test('Record with {}{} field (set to {!r}) -> PODS -> Record'.format(
        'nullable ' if nullable_or_not is nullable else '',
        class_name,
        value,
    ))
    def _():
        class MyRecord(Record):
            field = nullable_or_not(cls)
        r1 = MyRecord(field=value)
        d = r1.record_pods()
        assert_isinstance(d, dict)
        r2 = MyRecord.from_pods(d)
        assert_eq(r1.field, r2.field)

# @test('2016-04-15 - weird bug with serializing null values?')
# def _():
#     Item = record (
#         'Item',
#         one = nullable(text_type),
#         two = seq_of(int),
#     )
#     Collection = record ('Collection', items=seq_of(Item))
#     c = Collection([Item(one=None, two=[1, 2, 3])])
#     d = json.loads(c.json_dumps())
#     assert_eq (d, {
#         'items': [{
#             'two': [1, 2, 3]
#         }]
#     })

#----------------------------------------------------------------------------------------------------------------------------------
# duck-typing which classes can be serialized to PODS

@test("the nested object can be anything with a `record_pods' method")
def _():
    class Name(object):
        def __init__(self, first, last):
            self.first = first
            self.last = last
        def record_pods(self):
            return [self.first, self.last]
    class Person(Record):
        name = Name
        age = int
    p = Person(name=Name(first='Robert', last='Smith'), age=100)
    d = p.record_pods()
    assert_eq(d, {
        'name': ['Robert', 'Smith'],
        'age': 100,
    })

@test("If a class has a member with no `record_pods' method, it can still be instantiated, but it can't be serialized to a PODS")
def _():
    Name = namedtuple('Name', ('name',))
    class MyRecord(Record):
        name = Name
    r = MyRecord(Name('peter'))
    with assert_raises(CannotBeSerializedToPods):
        r.record_pods()

#----------------------------------------------------------------------------------------------------------------------------------
# duck-typing which classes can be deserialized from PODS

@test("anything with a `from_pods' method can be parsed from a PODS")
def _():
    class Name(object):
        def __init__(self, first, last):
            self.first = first
            self.last = last
        @classmethod
        def from_pods(cls, data):
            return cls(*data.split('/'))
        def __eq__(self, other):
            return self.first == other.first and self.last == other.last
        def __repr__(self):
            return 'Name(%r, %r)' % (self.first, self.last)
    class MyRecord(Record):
        name = Name
    assert_eq(
        MyRecord.from_pods({'name': 'Arthur/Smith'}),
        MyRecord(Name('Arthur', 'Smith')),
    )

@test("If a class has a member with no `from_pods' method, it can still be instantiated, but it can't be parsed from a PODS")
def _():
    Name = namedtuple('Name', ('name',))
    class MyRecord(Record):
        name = Name
    MyRecord(Name('peter'))
    class CantTouchThis(object):
        def __getattr__(self, attr):
            # ensure that the value given to `from_pods' below isn't even looked at in any way
            raise Exception('boom')
    with assert_raises(CannotBeSerializedToPods):
        MyRecord.from_pods(CantTouchThis())

#----------------------------------------------------------------------------------------------------------------------------------
# collections

@test('sequence fields get serialized to plain lists')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=[1, 2, 3])
    assert_eq(r.record_pods(), {
        'elems': [1, 2, 3],
    })

@test('pair fields get serialized to plain lists')
def _():
    class MyRecord(Record):
        elems = pair_of(int)
    r = MyRecord(elems=[1, 2])
    assert_eq(r.record_pods(), {
        'elems': [1, 2],
    })

@test('set_of fields get serialized to plain lists')
def _():
    class MyRecord(Record):
        elems = set_of(int)
    r = MyRecord(elems=[1, 2, 3])
    elems = r.record_pods()['elems']
    assert isinstance(elems, list), repr(elems)
    assert_eq(
        sorted(elems),
        [1, 2, 3],
    )

@test('dict_of fields get serialized to plain dicts')
def _():
    class MyRecord(Record):
        elems = dict_of(text_type, int)
    r = MyRecord(elems={'uno':1, 'zwei':2})
    assert_eq(r.record_pods(), {
        'elems': {'uno':1, 'zwei':2},
    })

@test("an empty dict gets serialized to '{}'")
def _():
    class MyRecord(Record):
        v = dict_of(text_type, text_type)
    assert_eq(MyRecord({}).record_pods(), {
        'v': {},
    })

#----------------------------------------------------------------------------------------------------------------------------------
# handling of null values

@test('null fields are not included in the a PODS')
def _():
    class MyRecord(Record):
        x = int
        y = nullable(int)
    r = MyRecord(x=1, y=None)
    d = r.record_pods()
    assert_eq(d, {'x':1})

@test("explicit 'null' values can be parsed from a PODS")
def _():
    class MyRecord(Record):
        x = int
        y = nullable(int)
    r0 = MyRecord(11)
    r1 = MyRecord.from_pods({'x':11})
    r2 = MyRecord.from_pods({'x':11, 'y':None})
    assert_eq(r1, r0)
    assert_eq(r2, r0)
    assert_eq(r1, r2)

@test('if the field is not nullable, FieldNotNullable is raised when parsing an explicit null')
def _():
    class MyRecord(Record):
        x = int
        y = int
    with assert_raises(FieldNotNullable):
        MyRecord.from_pods({'x':11, 'y':None})

@test('if the field is not nullable, FieldNotNullable is raised when parsing an implicit null')
def _():
    class MyRecord(Record):
        x = int
        y = int
    with assert_raises(FieldNotNullable):
        MyRecord.from_pods({'x':11})

#----------------------------------------------------------------------------------------------------------------------------------
# built-in marshallers

@foreach((
    (datetime(2009, 10, 28, 8, 53, 2), '2009-10-28T08:53:02'),
    (Decimal('10.3'), '10.3'),
))
def _(obj, marshalled_text):

    @test('{} objects automatically get marshalled and unmarshalled as expected'.format(obj.__class__.__name__))
    def _():
        class MyRecord(Record):
            fobj = obj.__class__
        r1 = MyRecord(obj)
        d = r1.record_pods()
        assert_eq(d, {'fobj': marshalled_text})
        assert_eq(r1, MyRecord.from_pods(d))

#----------------------------------------------------------------------------------------------------------------------------------
# custom marshallers

@test('fields can be serialized and deserialized using custom marshallers')
def _():
    Point = namedtuple('Point', ('x', 'y'))
    marshaller = Marshaller(
        lambda pt: '%d,%d' % pt,
        lambda s: Point(*map(int, s.split(','))),
    )
    with temporary_marshaller_registration(Point, marshaller):
        class MyRecord(Record):
            pt = Point
        r1 = MyRecord(Point(1, 2))
        assert_eq(
            r1.record_pods(),
            {'pt': '1,2'},
        )
        assert_eq(
            MyRecord.from_pods(r1.record_pods()),
            r1,
        )

@test('the marshaller must be available when the class is compiled, not when record_pods() is called')
def _():
    Point = namedtuple('Point', ('x', 'y'))
    marshaller = Marshaller(
        lambda pt: '%d,%d' % pt,
        lambda s: Point(*map(int, s.split(','))),
    )
    class MyRecord(Record):
        pt = Point
    with temporary_marshaller_registration(Point, marshaller):
        with assert_raises(CannotBeSerializedToPods):
            MyRecord(Point(1, 2)).record_pods()

#----------------------------------------------------------------------------------------------------------------------------------

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple
from decimal import Decimal

# tdds
from tdds import Cleaner, Record, dict_of, seq_of, set_of
from tdds.utils.compatibility import text_type

# this module
from .plumbing import assert_eq, build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test('cleaner can clean fields by name')
def _():
    class MyRecord(Record):
        myvalue = int
    class MyClass(Cleaner):
        def clean_myvalue(self, value):
            return int(value) * 2
    assert_eq(
        MyClass().clean(MyRecord, {'myvalue': '21'}),
        {'myvalue': 42},
    )

#----------------------------------------------------------------------------------------------------------------------------------

@test('cleaner can clean int fields')
def _():
    class MyRecord(Record):
        value = int
    assert_eq(
        Cleaner().clean(MyRecord, {'value': '42'}),
        {'value': 42},
    )

@test('cleaner can clean float fields')
def _():
    class MyRecord(Record):
        value = float
    assert_eq(
        Cleaner().clean(MyRecord, {'value': '4.2'}),
        {'value': 4.2},
    )

@test('cleaner can clean decimal fields')
def _():
    class MyRecord(Record):
        value = Decimal
    assert_eq(
        Cleaner().clean(MyRecord, {'value': '4.2'}),
        {'value': Decimal('4.2')},
    )

#----------------------------------------------------------------------------------------------------------------------------------

@test('cleaner subclass can define how ints are parsed')
def _():
    class MyRecord(Record):
        value = int
    class MyClass(Cleaner):
        def clean_int(self, value):
            return int(''.join(value))
    assert_eq(
        MyClass().clean(MyRecord, {'value': ['4', '2']}),
        {'value': 42},
    )

@test('cleaner subclass can define how floats are parsed')
def _():
    class MyRecord(Record):
        value = float
    class MyClass(Cleaner):
        def clean_float(self, value):
            return float('.'.join(value))
    assert_eq(
        MyClass().clean(MyRecord, {'value': ['4', '2']}),
        {'value': 4.2},
    )

@test('cleaner subclass can define how decimals are parsed')
def _():
    class MyRecord(Record):
        value = Decimal
    class MyClass(Cleaner):
        def clean_decimal(self, value):
            return Decimal('.'.join(value))
    assert_eq(
        MyClass().clean(MyRecord, {'value': ['4', '2']}),
        {'value': Decimal('4.2')},
    )

#----------------------------------------------------------------------------------------------------------------------------------

@test('cleaner subclass can define how list elems are parsed')
def _():
    class MyRecord(Record):
        mylist = seq_of(int)
    class MyClass(Cleaner):
        def clean_mylist_element(self, value):
            return int(value[2:])
    assert_eq(
        MyClass().clean(MyRecord, {'mylist': ['::10', '<>20']}),
        {'mylist': (10, 20)},
    )

@test('cleaner subclass can define how set elems are parsed')
def _():
    class MyRecord(Record):
        myset = set_of(int)
    class MyClass(Cleaner):
        def clean_myset_element(self, value):
            return int(value[2:])
    assert_eq(
        MyClass().clean(MyRecord, {'myset': ['::10', '<>20']}),
        {'myset': frozenset([10, 20])},
    )

@test('cleaner subclass can define how dict elems are parsed')
def _():
    class MyRecord(Record):
        mydict = dict_of(int, int)
    class MyClass(Cleaner):
        def clean_mydict_key(self, value):
            return int(value[2:])
        def clean_mydict_value(self, value):
            return int(value[:-2])
    assert_eq(
        MyClass().clean(MyRecord, {'mydict': {'::10': '20::'}}),
        {'mydict': {10: 20}},
    )

@test('cleaner subclass can define how sub-records are parsed by full path')
def _():
    class Currency(Record):
        symbol = text_type
    class Price(Record):
        currency = Currency
        value = int
    class MyClass(Cleaner):
        def clean_currency_symbol(self, value):
            return value.upper()
    assert_eq(
        MyClass().clean(Price, {'currency': {'symbol': 'gbp'}, 'value': 10}),
        {'currency': {'symbol': 'GBP'}, 'value': 10},
    )

@test('cleaner subclass cannot define how sub-records are parsed by subrecord field id')
def _():
    class Currency(Record):
        symbol = text_type
    class Price(Record):
        currency = Currency
        value = int
    class MyClass(Cleaner):
        def clean_symbol(self, value):
            return value.upper()
    assert_eq(
        MyClass().clean(Price, {'currency': {'symbol': 'this stays lowercase'}, 'value': 10}),
        {'currency': {'symbol': 'this stays lowercase'}, 'value': 10},
    )

@test('cleaner subrecord can define how a subrecord in a list is parsed')
def _():
    class Wolf(Record):
        name = text_type
    class Pack(Record):
        # Incidently 'wolves' is a good example of the can of worms proper de-pluralisation is, Ruby on Rails notwithstanding
        wolves = seq_of(Wolf)
    class MyClass(Cleaner):
        def clean_wolves_element_name(self, value):
            return value.title()
    assert_eq(
        MyClass().clean(Pack, {'wolves': [{'name': 'BUCK'}, {'name': 'spitz'}]}),
        {'wolves': ({'name': 'Buck'}, {'name': 'Spitz'})},
    )

@test('cleaner subrecord can define how a list in a subrecord is parsed')
def _():
    class Roof(Record):
        materials = seq_of(text_type)
    class House(Record):
        roof = Roof
    class MyClass(Cleaner):
        def clean_roof_materials_element(self, value):
            return value.title()
    assert_eq(
        MyClass().clean(House, {'roof': {'materials': ['sLATE', 'cOPPER']}}),
        {'roof': {'materials': ('Slate', 'Copper')}},
    )

#----------------------------------------------------------------------------------------------------------------------------------

@test('cleaner does not complain about unknown fields')
def _():
    class MyRecord(Record):
        value = int
    assert_eq(
        Cleaner().clean(MyRecord, {'value': 10, 'other': 11}),
        {'value': 10},
    )

@test('cleaner does not complain about missing values')
def _():
    class MyRecord(Record):
        value = int
    assert_eq(
        Cleaner().clean(MyRecord, {}),
        {'value': None},
    )

@test('field name cleaner takes precendence over field type')
def _():
    MyType = namedtuple('MyType', ('x',))
    class MyRecord(Record):
        myvalue = MyType
    class MyClass(Cleaner):
        def clean_mytype(self, _value_unused):
            return MyType(x=1)
        def clean_myvalue(self, _value_unused):
            return MyType(x=2)
    assert_eq(
        MyClass().clean(MyRecord, {'myvalue': 'ignored'}),
        {'myvalue': MyType(x=2)},
    )

#----------------------------------------------------------------------------------------------------------------------------------

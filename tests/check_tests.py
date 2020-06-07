#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# tdds
from tdds import Field, FieldNotNullable, FieldValueError, Record, SourceCodeTemplate, nullable
from tdds.utils.compatibility import text_type

# this module
from .plumbing import assert_eq, assert_is, assert_raises, build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# check function specified as a callable

@test("a 'check' function specified as any callable can validate the value")
def _():
    class SingleDigit(object):
        def __call__(self, v):
            return 0 <= v < 10
    class MyRecord(Record):
        id = Field(
            type=int,
            check=SingleDigit(),
        )
    assert_eq(MyRecord(7).id, 7)
    with assert_raises(FieldValueError, 'MyRecord.id: 17 is not a valid value'):
        MyRecord(17)

#----------------------------------------------------------------------------------------------------------------------------------
# check function specified as a string

@test("a 'check' function specified as a string can validate the value")
def _():
    class MyRecord(Record):
        id = Field(
            type=int,
            check='0 <= {} < 10',
        )
    assert_eq(MyRecord(7).id, 7)
    with assert_raises(FieldValueError, 'MyRecord.id: 17 is not a valid value'):
        MyRecord(17)

@test("a 'check' function specified as a string must contain a '{}'")
def _():
    with assert_raises(ValueError, 'len(%s) == 3'):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check='len(%s) == 3',
            )

@test("a 'check' function specified as a string must contain a '{}' with nothing in it")
def _():
    with assert_raises(ValueError, 'len({0}) == 3'):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check='len({0}) == 3',
            )

@test("a 'check' function specified as a string may not contain more than one '{}'")
def _():
    with assert_raises(ValueError, '{} == {}.upper()'):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check='{} == {}.upper()',
            )

#----------------------------------------------------------------------------------------------------------------------------------
# 'check' function specified as a SourceCodeGenerator

@test("a 'check' function can be specified as a SourceCodeGenerator")
def _():
    class MyRecord(Record):
        id = Field(
            type=int,
            check=SourceCodeTemplate(
                '$single_digit({})',
                single_digit=lambda v: 0 <= v < 10,
            ),
        )
    assert_eq(MyRecord(7).id, 7)
    with assert_raises(FieldValueError, 'MyRecord.id: 17 is not a valid value'):
        MyRecord(17)

@test("a 'check' function specified as a SourceCodeTemplate must contain a '{}'")
def _():
    with assert_raises(ValueError):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check=SourceCodeTemplate(
                    '$isupper(%s)',
                    isupper=lambda s: s == s.upper(),
                ),
            )

@test("a 'check' function specified as a SourceCodeTemplate must contain a '{}' with nothing in it")
def _():
    with assert_raises(ValueError):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check=SourceCodeTemplate(
                    '$isupper({0})',
                    isupper=lambda s: s == s.upper(),
                ),
            )

@test("a 'check' function specified as a SourceCodeTemplate may not contain more than one '{}'")
def _():
    with assert_raises(ValueError):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check=SourceCodeTemplate(
                    '$isupper({},{})',
                    isupper=lambda s: s == s.upper(),
                ),
            )

#----------------------------------------------------------------------------------------------------------------------------------
# what the check function receives, and when it is called

@test("the 'check' function is invoked after the null check and will not receive a None value if the field is not nullable")
def _():
    class SpecificError(Exception):
        pass
    def not_none(value):
        if value is None:
            raise SpecificError()
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=not_none,
        )
    with assert_raises(FieldNotNullable, 'MyRecord.id cannot be None'):
        MyRecord(None)

@test("the 'check' function will not receive a None value when the field is nullable, either")
def _():
    class SpecificError(Exception):
        pass
    def not_none(value):
        if value is None:
            raise SpecificError()
    class MyRecord(Record):
        id = Field(
            type=text_type,
            nullable=True,
            check=not_none,
        )
    assert_is(None, MyRecord(None).id)

@test('if both a default value and a check are provided, the check is invoked on the default value, too')
def _():
    class MyRecord(Record):
        id = Field(
            type=int,
            nullable=True,
            default=100,
            check=lambda v: 0 < v < 10,
        )
    with assert_raises(FieldValueError, 'MyRecord.id: 100 is not a valid value'):
        MyRecord()

#----------------------------------------------------------------------------------------------------------------------------------
# what the check function returns/raises

@test("if the 'check' function returns False, a FieldValueError exception is raised")
def _():
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=lambda s: s == 'valid',
        )
    with assert_raises(FieldValueError, "MyRecord.id: 'invalid' is not a valid value"):
        MyRecord('invalid')

@test("if the 'check' function returns True, no FieldValueError exception is raised")
def _():
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=lambda s: s == 'valid',
        )
    MyRecord('valid')

@test('the check function can return any truthy value')
def _():
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=re.compile(r'brac').search,
        )
    assert_eq(MyRecord('abracadabra').id, 'abracadabra')

@test('the check function can return any falsy value')
def _():
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=re.compile(r'brac').search,
        )
    with assert_raises(FieldValueError, "MyRecord.id: 'abragadabra' is not a valid value"):
        MyRecord('abragadabra')

@test("the 'check' function may raise exceptions, these are not caught and bubble up")
def _():
    def boom(value):
        raise BufferError('boom')
    class MyRecord(Record):
        id = Field(
            type=text_type,
            check=boom,
        )
    with assert_raises(BufferError, 'boom'):
        MyRecord('a')

@test('the coercion function runs before the check, and may change a bad value to a good one')
def _():
    class MyRecord(Record):
        id = Field(
            type=text_type,
            coerce=lambda s: s.upper(),
            check=lambda s: s == s.upper(),
        )
    r2 = MyRecord('ok')
    assert_eq(r2.id, 'OK')

@test('the output of the coercion function is passed to the check function, which may reject it')
def _():
    class MyRecord(Record):
        id = Field(
            type=int,
            coerce=lambda v: v + 10,
            check=lambda v: 0 <= v < 10,
        )
    with assert_raises(FieldValueError, 'MyRecord.id: 17 is not a valid value'):
        MyRecord(7)

#----------------------------------------------------------------------------------------------------------------------------------
# the default value

@test('despite being compiled to source a string of code, the default value is used by reference')
def _():
    obj = object()
    class MyRecord(Record):
        value = nullable(object, default=obj)
    r = MyRecord()
    assert_is(r.value, obj)

@test("the default value doesn't need a __repr__ that compiles as valid Python code")
def _():
    class MyClass(object):
        def __init__(self, value):
            self.value = value
        def __repr__(self):
            return '<{}>'.format(self.value)
    class MyRecord(Record):
        id = Field(
            type=MyClass,
            nullable=True,
            default=MyClass(10),
        )
    assert_eq(MyRecord().id.value, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# misc

@test("specifying something other than a string, a SourceCodeGenerator or a callable as 'check' raises a TypeError")
def _():
    with assert_raises(TypeError, '0'):
        class MyRecord(Record):  # pylint: disable=unused-variable
            id = Field(
                type=text_type,
                check=0,
            )

#----------------------------------------------------------------------------------------------------------------------------------

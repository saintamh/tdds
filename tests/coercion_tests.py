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

# record
from record import *
from record.utils.compatibility import text_type

# this module
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# "coerce" function specified as a callable

@test("a 'coerce' function specified as a lambda can modify the value")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = lambda s: s.upper(),
        )
    r = R('a')
    assert_eq(r.id, 'A')

@test("a 'coerce' function specified as any callable can modify the value")
def _():
    class Upper(object):
        def __call__(self, s):
            return s.upper()
    class R(Record):
        id = Field(
            type = text_type,
            coerce = Upper(),
        )
    r = R('a')
    assert_eq(r.id, 'A')

#----------------------------------------------------------------------------------------------------------------------------------
# "coerce" function specified as a string

@test("a 'coerce' function specified as a string can modify the value")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = '{}.upper()',
        )
    r = R('a')
    assert_eq(r.id, 'A')

@test("a 'coerce' function specified as a string must contain a '{}'")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = '%s.upper()',
            )

@test("a 'coerce' function specified as a string must contain a '{}' with nothing in it")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = '{0}.upper()',
            )

@test("a 'coerce' function specified as a string may not contain more than one '{}'")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = '{}.upper({})',
            )

#----------------------------------------------------------------------------------------------------------------------------------
# "coerce" function specified as a SourceCodeGenerator

@test("a 'coerce' function specified as a SourceCodeGenerator can modify the value")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = SourceCodeTemplate(
                '$upper({})',
                upper = lambda s: s.upper(),
            ),
        )
    assert_eq(R('a').id, 'A')

@test("a 'coerce' function specified as a SourceCodeTemplate must contain a '{}'")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = SourceCodeTemplate(
                    '$upper(%s)',
                    upper = lambda s: s.upper(),
                ),
            )

@test("a 'coerce' function specified as a SourceCodeTemplate must contain a '{}' with nothing in it")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = SourceCodeTemplate(
                    '$upper({0})',
                    upper = lambda s: s.upper(),
                ),
            )

@test("a 'coerce' function specified as a SourceCodeTemplate may not contain more than one '{}'")
def _():
    with expected_error(ValueError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = SourceCodeTemplate(
                    '$upper({},{})',
                    upper = lambda s: s.upper(),
                ),
            )

#----------------------------------------------------------------------------------------------------------------------------------
# checks on what the coerce function receives

@test("the 'coerce' function is invoked before the null check and therefore may get a None value")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = text_type,
        )
    r = R(None)
    assert_eq(r.id, 'None')

@test("if the field is nullable, the coercion function is run on the default value")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            nullable = True,
            default = 'lower',
            coerce = lambda v: v.upper(),
        )
    r = R(id=None)
    assert_eq(r.id, 'LOWER')

#----------------------------------------------------------------------------------------------------------------------------------
# checks on what the coerce function returns

@test("the 'coerce' function may not return None if the field is not nullable")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = lambda s: None,
        )
    with expected_error(FieldNotNullable):
        r = R('a')

@test("the 'coerce' function may return None if the field is nullable")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = lambda s: None,
            nullable = True,
        )
    r = R('a')
    assert_none(r.id)

@test("the coercion function must return a value of the correct type")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = lambda v: 10,
        )
    with expected_error(FieldTypeError):
        R(id='not ten')

@test("if the field is not nullable, the coercion function may not return None")
def _():
    class R(Record):
        id = Field(
            type = text_type,
            coerce = lambda v: None,
        )
    with expected_error(FieldNotNullable):
        R(id='not None')

#----------------------------------------------------------------------------------------------------------------------------------
# misc

@test("unlike in struct.py, the coerce function is always called, even if the value is of the correct type")
def _():
    all_vals = []
    def coercion(value):
        all_vals.append(value)
        return value
    class R(Record):
        id = Field(
            type = int,
            coerce = coercion,
        )
    R(10)
    assert_eq(all_vals, [10])

@test("specifying something other than a string, a SourceCodeGenerator or a callable as 'coerce' raises a TypeError")
def _():
    with expected_error(TypeError):
        class R(Record):
            id = Field(
                type = text_type,
                coerce = 0,
            )

#----------------------------------------------------------------------------------------------------------------------------------

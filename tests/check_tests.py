#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import re

# saintamh
from ...util.codegen import SourceCodeTemplate

# this module
from .. import *
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# check function specified as a callable

@test("a 'check' function specified as any callable can validate the value")
def _():
    class Upper (object):
        def __call__ (self, s):
            return s == 'valid'
    class R (Record):
        id = Field (
            type = str,
            check = Upper(),
        )
    assert_eq (R('valid').id, 'valid')
    with expected_error(FieldValueError):
        R('invalid')

#----------------------------------------------------------------------------------------------------------------------------------
# check function specified as a string

@test("a 'check' function specified as a string can validate the value")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = '{} == "valid"',
        )
    assert_eq (R('valid').id, 'valid')
    with expected_error(FieldValueError):
        R('invalid')

@test("a 'check' function specified as a string must contain a '{}'")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = 'len(%s) == 3',
            )

@test("a 'check' function specified as a string must contain a '{}' with nothing in it")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = 'len({0}) == 3',
            )

@test("a 'check' function specified as a string may not contain more than one '{}'")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = '{} == {}.upper()',
            )

#----------------------------------------------------------------------------------------------------------------------------------
# "check" function specified as a SourceCodeGenerator

@test("a 'check' function specified as a SourceCodeGenerator can modify the value")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = SourceCodeTemplate (
                '$isupper({})',
                isupper = lambda s: s == s.upper(),
            ),
        )
    assert_eq (R('A').id, 'A')
    with expected_error(FieldValueError):
        R('a')

@test("a 'check' function specified as a SourceCodeTemplate must contain a '{}'")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = SourceCodeTemplate (
                    '$isupper(%s)',
                    isupper = lambda s: s == s.upper(),
                ),
            )

@test("a 'check' function specified as a SourceCodeTemplate must contain a '{}' with nothing in it")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = SourceCodeTemplate (
                    '$isupper({0})',
                    isupper = lambda s: s == s.upper(),
                ),
            )

@test("a 'check' function specified as a SourceCodeTemplate may not contain more than one '{}'")
def _():
    with expected_error(ValueError):
        class R (Record):
            id = Field (
                type = str,
                check = SourceCodeTemplate (
                    '$isupper({},{})',
                    isupper = lambda s: s == s.upper(),
                ),
            )

#----------------------------------------------------------------------------------------------------------------------------------
# what the check function receives, and when it is called

@test("the 'check' function is invoked after the null check and will not receive a None value if the field is not nullable")
def _():
    class SpecificError(Exception):
        pass
    def not_none (value):
        if value is None:
            raise SpecificError()
    class R (Record):
        id = Field (
            type = str,
            check = not_none,
        )
    with expected_error(FieldNotNullable):
        r = R(None)

@test("the 'check' function will not receive a None value when the field is nullable, either")
def _():
    class SpecificError(Exception):
        pass
    def not_none (value):
        if value is None:
            raise SpecificError()
    class R (Record):
        id = Field (
            type = str,
            nullable = True,
            check = not_none,
        )
    assert_is (None, R(None).id)

@test("if both a default value and a check are provided, the check is invoked on the default value, too")
def _():
    class R (Record):
        id = Field (
            type = str,
            nullable = True,
            default = 'abra',
            check = lambda s: value == 'cadabra',
        )

#----------------------------------------------------------------------------------------------------------------------------------
# what the check function returns/raises

@test("if the 'check' function returns False, a FieldValueError exception is raised")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = lambda s: s == 'valid',
        )
    with expected_error(FieldValueError):
        R('invalid')

@test("if the 'check' function returns True, no FieldValueError exception is raised")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = lambda s: s == 'valid',
        )
    r = R('valid')

@test("the check function can return any truthy value")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = re.compile(r'brac').search,
        )
    assert_eq (R('abracadabra').id, 'abracadabra')

@test("the check function can return any falsy value")
def _():
    class R (Record):
        id = Field (
            type = str,
            check = re.compile(r'brac').search,
        )
    with expected_error(FieldValueError):
        R('abragadabra')

@test("the 'check' function may raise exceptions, these are not caught and bubble up")
def _():
    def boom (value):
        raise BufferError ('boom')
    class R (Record):
        id = Field (
            type = str,
            check = boom,
        )
    with expected_error(BufferError):
        r = R('a')

@test("the coercion function runs before the check, and may change a bad value to a good one")
def _():
    class R (Record):
        id = Field (
            type = str,
            coerce = lambda s: s.upper(),
            check = lambda s: s == s.upper(),
        )
    r2 = R('ok')
    assert_eq (r2.id, 'OK')

@test("the output of the coercion function is passed to the check function, which may reject it")
def _():
    class R (Record):
        id = Field (
            type = str,
            coerce = lambda s: s.lower(),
            check = lambda s: s == s.upper(),
        )
    with expected_error(FieldValueError):
        r2 = R('OK')

#----------------------------------------------------------------------------------------------------------------------------------
# the default value

@test("despite being compiled to source a string of code, the default value is used by reference")
def _():
    obj = object()
    class R (Record):
        val = nullable(object, default=obj)
    r = R()
    assert_is (r.val, obj)

@test("the default value doesn't need a __repr__ that compiles as valid Python code")
def _():
    class C (object):
        def __init__ (self, value):
            self.value = value
        def __repr__ (self):
            return '<{}>'.format(self.value)
    class R (Record):
        id = Field (
            type = C,
            nullable = True,
            default = C(10),
        )
    assert_eq (R().id.value, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# misc

@test("specifying something other than a string, a SourceCodeGenerator or a callable as 'check' raises a TypeError")
def _():
    with expected_error(TypeError):
        class R (Record):
            id = Field (
                type = str,
                check = 0,
            )

#----------------------------------------------------------------------------------------------------------------------------------

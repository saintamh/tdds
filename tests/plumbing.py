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

# standards
from contextlib import contextmanager
import re
from traceback import print_exc

# record
from record.utils.compatibility import string_types

#----------------------------------------------------------------------------------------------------------------------------------

class TestFailure(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

def build_test_registry():
    ALL_TESTS = []
    def test(test_id):
        def register_test_func(func):
            if any(prev_test_id == test_id for prev_test_id, prev_func in ALL_TESTS):
                raise ValueError("Two tests with id '%s'" % test_id)
            ALL_TESTS.append((test_id, func))
            return func
        return register_test_func
    return ALL_TESTS, test

def foreach(args):
    def register(func):
        for a in args:
            if not isinstance(a, tuple):
                a = (a,)
            func(*a)
    return register

#----------------------------------------------------------------------------------------------------------------------------------

@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except Exception as exception:
        if not isinstance(exception, exc_type):
            raise AssertionError("Expected %s, got %s: %s" % (exc_type.__name__, exception.__class__.__name__, exception))
    else:
        raise AssertionError("Expected %s, no exception raised" % exc_type.__name__)

def assert_eq(v1, v2):
    if v1 != v2:
        raise AssertionError("%r != %r" % (v1, v2))

def assert_is(v1, v2):
    if v1 is not v2:
        raise AssertionError("%r is not %r" % (v1, v2))

def assert_isinstance(v, cls):
    if not isinstance(v, cls):
        raise AssertionError("%r is not a %s instance" % (v, cls.__name__))

def assert_none(v):
    if v is not None:
        raise AssertionError("Expected None, got %r" % (v,))

def assert_matches(regex, text):
    if isinstance(regex, string_types):
        regex = re.compile(regex)
    if not regex.search(text):
        raise AssertionError("%r does not match /%s/" % (text, regex.pattern))

#----------------------------------------------------------------------------------------------------------------------------------

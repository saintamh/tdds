#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import contextmanager
from functools import partial
import re

# tdds
from tdds.utils.compatibility import PY2, string_types

#----------------------------------------------------------------------------------------------------------------------------------

class TestFailure(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

def build_test_registry():
    all_tests = []
    def test(test_id, *args, **kwargs):
        def register_test_func(func):
            if any(prev_test_id == test_id for prev_test_id, prev_func in all_tests):
                raise ValueError("Two tests with id '%s'" % test_id)
            all_tests.append((test_id, partial(func, *args, **kwargs)))
        return register_test_func
    return all_tests, test

def foreach(args):
    def register(func):
        for a in args:
            if not isinstance(a, tuple):
                a = (a,)
            func(*a)
    return register

#----------------------------------------------------------------------------------------------------------------------------------

@contextmanager
def assert_raises(exc_type, message=None):
    try:
        yield
    except Exception as exception:
        if not isinstance(exception, exc_type):
            raise AssertionError('Expected %s, got %s: %s' % (exc_type.__name__, exception.__class__.__name__, exception))
        actual_message = str(exception)
        if PY2:
            actual_message = re.sub(r"\bu(?=')", '', actual_message)
        if message is not None and actual_message != message:
            raise AssertionError('Expected %r, got %r' % (message, actual_message))
    else:
        raise AssertionError('Expected %s, no exception raised' % exc_type.__name__)

def assert_eq(v1, v2):
    if v1 != v2:
        raise AssertionError('%r != %r' % (v1, v2))

def assert_is(v1, v2):
    if v1 is not v2:
        raise AssertionError('%r is not %r' % (v1, v2))

def assert_isinstance(v, cls):
    if not isinstance(v, cls):
        raise AssertionError('%r is not a %s instance' % (v, cls.__name__))

def assert_none(v):
    if v is not None:
        raise AssertionError('Expected None, got %r' % (v,))

def assert_matches(regex, text):
    if isinstance(regex, string_types):
        regex = re.compile(regex)
    if not regex.search(text):
        raise AssertionError('%r does not match /%s/' % (text, regex.pattern))

#----------------------------------------------------------------------------------------------------------------------------------

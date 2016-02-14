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
from traceback import print_exc

#----------------------------------------------------------------------------------------------------------------------------------

class TestFailure (Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

def build_test_registry ():
    ALL_TESTS = []
    def test (test_id):
        def register_test_func (func):
            if any (prev_test_id == test_id for prev_test_id,prev_func in ALL_TESTS):
                raise ValueError ("Two tests with id '%s'" % test_id)
            ALL_TESTS.append ((test_id, func))
            return func
        return register_test_func
    return ALL_TESTS,test

def foreach (args):
    def register (func):
        for a in args:
            if not isinstance(a,tuple):
                a = (a,)
            func(*a)
    return register

#----------------------------------------------------------------------------------------------------------------------------------

class expected_error (object):
    def __init__ (self, exc_type):
        self.exc_type = exc_type
    def __enter__ (self):
        pass
    def __exit__ (self, exc_type, exc_value, exc_tb):
        if exc_type is self.exc_type:
            return True # swallow the exception, test passes
        elif exc_type is None:
            raise TestFailure ("Expected %s, no exception raised" % self.exc_type.__name__)
        else:
            print_exc()
            raise TestFailure ("Expected %s, got %s: %s" % (self.exc_type.__name__, exc_type.__name__, exc_value))

def assert_eq (v1, v2):
    if v1 != v2:
        raise AssertionError ("%r != %r" % (v1,v2))

def assert_is (v1, v2):
    if v1 is not v2:
        raise AssertionError ("%r is not %r" % (v1,v2))

def assert_isinstance (v, cls):
    if not isinstance (v, cls):
        raise AssertionError ("%r is not a %s instance" % (v,cls.__name__))

def assert_none (v):
    if v is not None:
        raise AssertionError ("Expected None, got %r" % (v,))

#----------------------------------------------------------------------------------------------------------------------------------

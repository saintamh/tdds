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
from collections import namedtuple
from datetime import date, datetime

# record
from record.marshaller import Marshaller, lookup_marshaller_for_type, temporary_marshaller_registration
from record.utils.compatibility import bytes_type, integer_types, text_type

# this module
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@foreach((
    #(b'abc \x01\x02\x03\x04', b'abc \x01\x02\x03\x04'),
    ('R\u00E9sum\u00E9', 'R\u00E9sum\u00E9'),
) + tuple(
    (t(42), text_type(t(42)))
    for t in integer_types
) + (
    (41.0, '41.0'),
    (date(2010, 10, 24), '2010-10-24'),
    (datetime(2010, 10, 24, 9, 5, 33), '2010-10-24T09:05:33'),
))
def _(value, marshalled_text):
    cls = value.__class__
    cls_name = cls.__name__
    marshaller = lookup_marshaller_for_type(cls)

    @test("%s fields can be marshalled" % cls_name)
    def _():
        assert_isinstance(
            marshaller.marshal(value),
            text_type
        )

    @test("%s fields have the expected marshalled byte representation" % cls_name)
    def _():
        assert_eq(
            marshaller.marshal(value),
            marshalled_text,
        )

    @test("%s fields marshalled to str can be unmarshalled" % cls_name)
    def _():
        assert_eq(
            value,
            marshaller.unmarshal(marshaller.marshal(value)),
        )

#----------------------------------------------------------------------------------------------------------------------------------

@test("temporary_marshaller_registration does just that")
def _():
    Point = namedtuple('Point', ('x','y'))
    assert_none(lookup_marshaller_for_type(Point))
    bogus_marshaller = Marshaller(
        lambda value: text_type(value),
        lambda v: None,
    )
    with temporary_marshaller_registration(Point,bogus_marshaller):
        assert_is(bogus_marshaller, lookup_marshaller_for_type(Point))
    assert_none(lookup_marshaller_for_type(Point))

# TODO: test DuckTypedMarshaller

#----------------------------------------------------------------------------------------------------------------------------------

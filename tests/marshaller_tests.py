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
from datetime import datetime

# this module
from .plumbing import *
from ..marshaller import STANDARD_MARSHALLERS

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@foreach ((
    ('abc \x01\x02\x03\x04', 'abc \x01\x02\x03\x04'),
    (u'R\u00E9sum\u00E9', 'R\xc3\xa9sum\xc3\xa9'),
    (42, '42'),
    (41.0, '41.0'),
    (2L, '2L'),
    (datetime (2010, 10, 24, 9, 5, 33), '2010-10-24T09:05:33'),
))
def _(value, marshalled_bytes):
    cls = value.__class__
    cls_name = cls.__name__
    marshaller = STANDARD_MARSHALLERS[cls]

    @test("%s fields can be marshalled" % cls_name)
    def _():
        assert_isinstance (
            marshaller.marshal(value),
            str
        )

    @test("%s fields have the expected marshalled byte representation" % cls_name)
    def _():
        assert_eq (
            marshaller.marshal(value),
            marshalled_bytes,
        )

    @test("%s fields marshalled to str can be unmarshalled" % cls_name)
    def _():
        assert_eq (
            value,
            marshaller.unmarshal (marshaller.marshal(value)),
        )

#----------------------------------------------------------------------------------------------------------------------------------

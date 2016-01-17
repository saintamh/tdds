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

# saintamh
from saintamh.util.codegen import ExternalValue, SourceCodeTemplate, compile_expr

# this module
from .utils import ExternalCodeInvocation

#----------------------------------------------------------------------------------------------------------------------------------
# constants, config

DT_FMT = '%Y-%m-%dT%H:%M:%S'

#----------------------------------------------------------------------------------------------------------------------------------

class Marshaller (object):

    def __init__ (self, marshalling_code, unmarshalling_code):
        # These can be either strings for code with exactly one '{}' in them, or SourceCodeGenerator objects that generate such a
        # string, or callable objects. They'll be made into ExternalCodeInvocation instances for insertion into the generated code.
        # 
        # `marshal' must return a `str' object, not unicode. That was it can be written to raw streams for serialization. I
        # considered allowing objects to be marshalled to `unicode' objects as well, because that's what the JSON encoder needs
        # (because unicode strings are seralized with \uXXXX escapes, rather than as UTF-8 bytes). But that made the code quite
        # thick and messy, so I dropped that, and the JSON encoder special-cases unicode objects. Any other custom scalar types
        # will have to marshal to `str'
        # 
        self.marshalling_code = marshalling_code
        self.unmarshalling_code = unmarshalling_code

        # These are here for tests and debugging, since normally you don't call the code directly, you insert it in a code template
        # 
        self.marshal,self.unmarshal = (
            compile_expr (
                SourceCodeTemplate (
                    'f = lambda v: $code',
                    code = ExternalCodeInvocation (code, 'v'),
                ),
                'f',
            )
            for code in (self.marshalling_code,self.unmarshalling_code)
        )

class CannotMarshalType (TypeError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
# standard types

STANDARD_MARSHALLERS = {

    str: Marshaller ('{}', '{}'),
    unicode: Marshaller (
        '{}.encode("UTF-8")',
        '{}.decode("UTF-8")',
    ),

    int: Marshaller (repr, int),
    long: Marshaller (repr, long),
    float: Marshaller (repr, float),
    bool: Marshaller (repr, bool),

    datetime: Marshaller (
        '{}.strftime(%r)' % DT_FMT,
        SourceCodeTemplate (
            '$datetime.strptime ({}, $fmt)',
            datetime = datetime,
            fmt = ExternalValue(DT_FMT),
        ),
    ),

}

#----------------------------------------------------------------------------------------------------------------------------------

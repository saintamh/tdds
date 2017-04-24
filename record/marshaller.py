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
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal

# this module
from .utils.codegen import ExternalCodeInvocation, ExternalValue, SourceCodeTemplate, compile_expr

#----------------------------------------------------------------------------------------------------------------------------------
# constants, config

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DATE_FORMAT = '%Y-%m-%d'

#----------------------------------------------------------------------------------------------------------------------------------

class Marshaller(object):

    def __init__(self, marshalling_code, unmarshalling_code):
        # These can be either strings for code with exactly one '{}' in them, or SourceCodeGenerator objects that generate such a
        # string, or callable objects. They'll be made into ExternalCodeInvocation instances for insertion into the generated code.
        # 
        # `marshal' must return a `str' object, not unicode. That way it can be written to raw streams for serialization. I
        # considered allowing objects to be marshalled to `unicode' objects as well, because that's what the JSON encoder needs
        # (because unicode strings are serialized with \uXXXX escapes, rather than as UTF-8 bytes). But that made the code quite
        # thick and messy, so I dropped that, and the JSON encoder special-cases unicode objects. Any other custom scalar types
        # will have to marshal to `str'
        # 
        self.marshalling_code = marshalling_code
        self.unmarshalling_code = unmarshalling_code

        # These are here for tests and debugging, since normally you don't call the code directly, you insert it in a code template
        # 
        self.marshal,self.unmarshal = (
            compile_expr(
                SourceCodeTemplate(
                    'f = lambda v: $code',
                    code = ExternalCodeInvocation(code, 'v'),
                ),
                'f',
            )
            for code in (self.marshalling_code,self.unmarshalling_code)
        )

#----------------------------------------------------------------------------------------------------------------------------------
# global vars

STANDARD_MARSHALLERS = {

    str: Marshaller('{}', '{}'),
    unicode: Marshaller(
        '{}.encode("UTF-8")',
        '{}.decode("UTF-8")',
    ),

    int: Marshaller(repr, int),
    long: Marshaller(repr, long),
    float: Marshaller(repr, float),
    bool: Marshaller(repr, bool),
    Decimal: Marshaller(str, Decimal),

    datetime: Marshaller(
        '{}.strftime(%r)' % DATETIME_FORMAT,
        SourceCodeTemplate(
            '$datetime.strptime ({}, $fmt)',
            datetime = datetime,
            fmt = ExternalValue(DATETIME_FORMAT),
        ),
    ),

    date: Marshaller(
        '{}.strftime(%r)' % DATE_FORMAT,
        SourceCodeTemplate(
            '$datetime.strptime({}, $fmt).date()',
            datetime = datetime,
            fmt = ExternalValue(DATE_FORMAT),
        ),
    ),

    timedelta: Marshaller(
        'str({}.total_seconds())',
        SourceCodeTemplate(
            '$timedelta(seconds=float({}))',
            timedelta = timedelta,
        ),
    ),

}

CUSTOM_MARSHALLERS = {}

#----------------------------------------------------------------------------------------------------------------------------------
# public interface for this module

class CannotMarshalType(TypeError):
    pass

def register_marshaller(cls, marshaller):
    CUSTOM_MARSHALLERS[cls] = marshaller

def unregister_marshaller(cls, marshaller):
    if CUSTOM_MARSHALLERS.get(cls) is marshaller:
        del CUSTOM_MARSHALLERS[cls]
    else:
        raise KeyError(cls)

def lookup_marshaller_for_type(cls):
    marshaller = CUSTOM_MARSHALLERS.get(cls)
    if marshaller is None:
        marshaller = STANDARD_MARSHALLERS.get(cls)
        if marshaller is None:
            if hasattr(getattr(cls,'marshall_to_str',None), '__call__') \
                    and hasattr(getattr(cls,'unmarshall_from_str',None), '__call__'):
                marshaller = DuckTypedMarshaller(cls)
    return marshaller

def lookup_marshalling_code_for_type(cls):
    marshaller = lookup_marshaller_for_type(cls)
    return marshaller and marshaller.marshalling_code

def lookup_unmarshalling_code_for_type(cls):
    marshaller = lookup_marshaller_for_type(cls)
    return marshaller and marshaller.unmarshalling_code

# The marshaller lookup dict is global, which is not great, but the alternative was to have to pass around a marshaller registry,
# which just didn't fit the model very well. I'm confident that normally if you have a marshaller to register for a type, you'll
# only have that one, and so a global is fine. Still, for situations where you might want to run just a block of code with a
# certain marshaller (which happens in tests), there's this context manager
@contextmanager
def temporary_marshaller_registration(cls, marshaller):
    register_marshaller(cls, marshaller)
    yield
    unregister_marshaller(cls, marshaller)

def wrap_in_null_check(nullable, value_expr, code):
    if nullable:
        return SourceCodeTemplate(
            'None if $value is None else $code',
            value = value_expr,
            code = code,
        )
    else:
        return code

#----------------------------------------------------------------------------------------------------------------------------------

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# this module
from .record import Field, compile_field
from .utils.codegen import SourceCodeTemplate
from .utils.compatibility import bytes_type, native_string, text_type

#----------------------------------------------------------------------------------------------------------------------------------

def value_check(name, check):
    def func(field):
        field = compile_field(field)
        if field.check is not None:
            raise Exception("I haven't looked into how to chain value checks yet")
        return field.derive(check=check)
    func.__name__ = native_string(name)
    return func

nonempty = value_check('nonempty', 'len({}) > 0')

nonnegative = value_check('nonnegative', '{} >= 0')
strictly_positive = value_check('strictly_positive', '{} > 0')

#----------------------------------------------------------------------------------------------------------------------------------

def regex_check(name, char_def):
    def func(n=None):
        multiplier = ('{{%d}}' % n) if n is not None else '*'
        field = Field(
            type=text_type,
            check="$re.search(r'^[%s]%s$',{})" % (char_def, multiplier),
        )
        return field
    func.__name__ = native_string(name)
    return func

uppercase_letters = regex_check('uppercase_letters', 'A-Z')
uppercase_wchars = regex_check('uppercase_wchars', 'A-Z0-9_')
uppercase_hex = regex_check('uppercase_hex', '0-9A-F')

lowercase_letters = regex_check('lowercase_letters', 'a-z')
lowercase_wchars = regex_check('lowercase_wchars', 'a-z0-9_')
lowercase_hex = regex_check('lowercase_hex', '0-9a-f')

digits_str = regex_check('digits_str', '0-9')

absolute_http_url = Field(
    type=bytes_type,
    check=SourceCodeTemplate(
        "$re.search(r'^https?://.{{1, 2000}}$', {})",
        re=re,
    ),
)

#----------------------------------------------------------------------------------------------------------------------------------
# other field def utils

class EnumField(Field):

    def __init__(self, type, possible_values, **kwargs):
        kwargs['check'] = possible_values.__contains__
        object.__setattr__(self, 'possible_values', possible_values)
        super(EnumField, self).__init__(type, **kwargs)

def one_of(*values, **kwargs):
    if len(values) == 0:
        raise ValueError('one_of requires arguments')
    type = values[0].__class__
    for v in values[1:]:
        if v.__class__ is not type:
            raise ValueError('All arguments to one_of should be of the same type (%s is not %s)' % (
                type.__name__,
                v.__class__.__name__,
            ))
    values = frozenset(values)
    return EnumField(type, values, **kwargs)

def nullable(field, default=None):
    return compile_field(field).derive(
        nullable=True,
        default=default,
    )

#----------------------------------------------------------------------------------------------------------------------------------

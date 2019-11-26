#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

#----------------------------------------------------------------------------------------------------------------------------------
# core data structures

class Field(object):

    def __init__(self, type, nullable=False, default=None, coerce=None, check=None, subfields=()):
        object.__setattr__(self, 'type', type)
        object.__setattr__(self, 'nullable', nullable)
        object.__setattr__(self, 'default', default)
        object.__setattr__(self, 'coerce', coerce)
        object.__setattr__(self, 'check', check)
        object.__setattr__(self, 'subfields', subfields)

    def __setattr__(self, attr, value):
        raise TypeError('Field objects are immutable')
    def __delattr__(self, attr):
        raise TypeError('Field objects are immutable')

    def set_recursive_type(self, ftype):
        if self.type is RecursiveType:
            object.__setattr__(self, 'type', ftype)
        for child in self.subfields:
            child.set_recursive_type(ftype)

    def derive(self, **kwargs):
        new_field = Field(
            self.type,
            kwargs.pop('nullable', self.nullable),
            kwargs.pop('default', self.default),
            kwargs.pop('coerce', self.coerce),
            kwargs.pop('check', self.check),
            self.subfields,
        )
        if kwargs:
            raise TypeError('gUnknown kwargs: %s' % ', '.join(sorted(kwargs)))
        return new_field

    def __repr__(self):
        return 'Field (%r%s%s%s%s)' % (
            self.type,
            ', nullable=True' if self.nullable else '',
            ', default=%r' % self.default if self.default else '',
            ', coerce=%r' % self.coerce if self.coerce else '',
            ', check=%r' % self.check if self.check else '',
        )

#----------------------------------------------------------------------------------------------------------------------------------
# public exception classes

class RecordsAreImmutable(TypeError):
    pass

class FieldError(ValueError):
    pass

class FieldValueError(FieldError):
    pass

class FieldTypeError(FieldError):
    pass

class FieldNotNullable(FieldValueError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
# If a field has `RecursiveType' as its `type', then that gets translated to the record's own class. This allows the user to define
# typed recursive data structures, e.g. LinkedLists, where the object has a field of the same type as itself.

class RecursiveType(object):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

def compile_field(field, **kwargs):
    if isinstance(field, Field):
        if kwargs:
            return field.derive(**kwargs)
        else:
            return field
    else:
        assert not kwargs, (field, kwargs)
        return Field(field)

#----------------------------------------------------------------------------------------------------------------------------------

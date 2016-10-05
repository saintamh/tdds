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
from collections import namedtuple

#----------------------------------------------------------------------------------------------------------------------------------
# core data structures

class Field (namedtuple ('Field', (
        'type',
        'nullable',
        'default',
        'coerce',
        'check',
        ))):

    def __new__ (cls, type, nullable=False, default=None, coerce=None, check=None):
        return super(Field,cls).__new__(cls, type, nullable, default, coerce, check)

    def derive (self, **kwargs):
        return self._replace(**kwargs)

    def __repr__ (self):
        return 'Field (%r%s%s%s%s)' % (
            self.type,
            ', nullable=True' if self.nullable else '',
            ', default=%r' % self.default if self.default else '',
            ', coerce=%r' % self.coerce if self.coerce else '',
            ', check=%r' % self.check if self.check else '',
        )

#----------------------------------------------------------------------------------------------------------------------------------
# public exception classes

class RecordsAreImmutable (TypeError):
    pass

class FieldError (ValueError):
    pass

class FieldValueError (FieldError):
    pass

class FieldTypeError (FieldError):
    pass

class FieldNotNullable (FieldValueError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

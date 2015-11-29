#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# core data structures

class Field (object):

    def __init__ (self, type, nullable=False, default=None, coerce=None, check=None):
        self.type = type
        self.nullable = nullable
        self.default = default
        self.coerce = coerce
        self.check = check

    def derive (self, nullable=None, default=None, coerce=None, check=None):
        return self.__class__ (
            type = self.type,
            nullable = self.nullable if nullable is None else nullable,
            default = self.default if default is None else default,
            coerce = self.coerce if coerce is None else coerce,
            check = self.check if check is None else check,
        )

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

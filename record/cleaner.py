#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from decimal import Decimal
import re

# this repo
from .utils.compatibility import bytes_type, text_type
from .utils.immutabledict import ImmutableDict

#----------------------------------------------------------------------------------------------------------------------------------

class Cleaner(object):

    def clean(self, record_class, values, prefix=''):
        values = dict(values)
        clean_values = {
            field_id: self._clean_field(
                field_id,
                field,
                values.pop(field_id, None),
                prefix=prefix,
            )
            for field_id, field in record_class.record_fields.items()
        }
        if values:
            raise TypeError("Unknown values: %s" % ','.join(sorted(values)))
        return clean_values

    def _clean_field(self, field_id, field, value, prefix=''):
        if value is None:
            return None
        clean_by_fname = getattr(
            self,
            'clean_%s%s' % (prefix, field_id),
            None,
        )
        if clean_by_fname:
            return clean_by_fname(value)
        if issubclass(field.type, tuple) and hasattr(field.type, 'element_field'):
            return tuple(
                self._clean_field(prefix + field_id + '_element', field.type.element_field, element)
                for element in value
            )
        if issubclass(field.type, frozenset) and hasattr(field.type, 'element_field'):
            return frozenset(
                self._clean_field(prefix + field_id + '_element', field.type.element_field, element)
                for element in value
            )
        if issubclass(field.type, ImmutableDict) and hasattr(field.type, 'key_field') and hasattr(field.type, 'value_field'):
            return {
                self._clean_field(field_id + '_key', field.type.key_field, key):
                    self._clean_field(field_id + '_value', field.type.value_field, value)
                for key, value in value.items()
            }
        if hasattr(field.type, 'record_fields') and isinstance(value, dict):
            try:
                return self.clean(field.type, value, prefix=(prefix + field_id + '_'))
            except Exception:
                raise ValueError("Couldn't clean '%s'" % (prefix + field_id))
        clean_by_type = self._cleaner_by_type(field)
        if clean_by_type:
            return clean_by_type(value)
        raise TypeError("Don't know how to clean %s '%s'" % (field.type.__name__, field_id))

    def _cleaner_by_type(self, field):
        type_name = {
            text_type: 'text',
            bytes_type: 'bytes',
        }.get(field.type)
        if type_name is None:
            type_name = re.sub(
                r'(?<=[a-z])(?=[A-Z])',
                '_',
                field.type.__name__,
            ).lower()
        return getattr(self, 'clean_%s' % type_name, None)

    def clean_text(self, value):
        if not isinstance(value, text_type):
            value = text_type(value)
        return value

    def clean_int(self, value):
        if not isinstance(value, int):
            value = int(self.clean_text(value))
        return value

    def clean_float(self, value):
        if not isinstance(value, float):
            value = float(self.clean_text(value))
        return value

    def clean_decimal(self, value):
        if not isinstance(value, Decimal):
            value = Decimal(self.clean_text(value))
        return value

#----------------------------------------------------------------------------------------------------------------------------------

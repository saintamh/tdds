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
        return {
            field_id: self._clean_field(
                field_id,
                field,
                values.pop(field_id, None),
                prefix=prefix,
            )
            for field_id, field in record_class.record_fields.items()
        }

    def _clean_field(self, field_id, field, value, prefix=''):
        if value is None:
            return None
        clean_by_fname = getattr(
            self,
            'clean_%s%s' % (prefix, field_id),
            None,
        )
        if clean_by_fname:
            cleaned = clean_by_fname(value)
        elif issubclass(field.type, tuple) and hasattr(field.type, 'element_field'):
            cleaned = tuple(
                self._clean_field(prefix + field_id + '_element', field.type.element_field, element)
                for element in value
            )
        elif issubclass(field.type, frozenset) and hasattr(field.type, 'element_field'):
            cleaned = frozenset(
                self._clean_field(prefix + field_id + '_element', field.type.element_field, element)
                for element in value
            )
        elif issubclass(field.type, ImmutableDict) and hasattr(field.type, 'key_field') and hasattr(field.type, 'value_field'):
            cleaned = {
                self._clean_field(field_id + '_key', field.type.key_field, key):
                    self._clean_field(field_id + '_value', field.type.value_field, value)
                for key, value in value.items()
            }
        elif hasattr(field.type, 'record_fields') and isinstance(value, dict):
            try:
                cleaned = self.clean(field.type, value, prefix=(prefix + field_id + '_'))
            except Exception:
                raise ValueError("Couldn't clean '%s'" % (prefix + field_id))
        else:
            clean_by_type = self._cleaner_by_type(field)
            if clean_by_type:
                value = clean_by_type(value)
            cleaned = value
        return cleaned

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

    def clean_bool(self, value):
        if not isinstance(value, bool):
            value = {
                'true': True,
                '1': True,
                'false': False,
                '0': False,
            }[self.clean_text(value).lower()]
        return value

#----------------------------------------------------------------------------------------------------------------------------------

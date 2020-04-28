#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PODS = Plain Old Data Structure = the standard Python data types only: dicts, lists, ints, str's, etc

This module contains methods for serializing record objects to and from simple, "plain" data structures. Although this isn't about
JSON specifically, the PODS should be immediately serializable to strings using the standard `json' module.
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import wraps

# this module
from .basics import RecursiveType
from .marshaller import lookup_marshalling_code_for_type, lookup_unmarshalling_code_for_type, wrap_in_null_check
from .utils.codegen import ExternalCodeInvocation, ExternalValue, Joiner, SourceCodeTemplate
from .utils.compatibility import integer_types, string_types, text_type

#----------------------------------------------------------------------------------------------------------------------------------

PODS_TYPES = frozenset(
    string_types
    + integer_types
    + (float, bool)
)

class CannotBeSerializedToPods(TypeError):
    pass

def serialization_exceptions_at_runtime(func):
    """
    This decorates functions that generate source code. If the source code generation raises CannotBeSerializedToPods, instead of
    throwing that exception at class compile time, we instead replace the code that would've been generated with a single 'raise'
    statement.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            if isinstance(ex, CannotBeSerializedToPods):
                return SourceCodeTemplate(
                    'raise $CannotBeSerializedToPods($mesg)',
                    CannotBeSerializedToPods=CannotBeSerializedToPods,
                    mesg=ExternalValue(text_type(ex)),
                )
            else:
                raise
    return wrapper

#----------------------------------------------------------------------------------------------------------------------------------

class PodsMethodsTemplate(SourceCodeTemplate):

    template = '''
        def record_pods (self):
            $record_pods_impl

        @classmethod
        def from_pods (cls, pods):
            $from_pods_impl
    '''

    @staticmethod
    def value_to_pods(value_expr, field, needs_null_check=True):
        if field.type in PODS_TYPES:
            return value_expr
        elif field.type is RecursiveType or callable(getattr(field.type, 'record_pods', None)):
            return wrap_in_null_check(
                field.nullable and needs_null_check,
                value_expr,
                '{}.record_pods()'.format(value_expr),
            )
        else:
            marshalling_code = lookup_marshalling_code_for_type(field.type)
            if marshalling_code is not None:
                return wrap_in_null_check(
                    field.nullable,
                    value_expr,
                    ExternalCodeInvocation(marshalling_code, value_expr)
                )
            else:
                raise CannotBeSerializedToPods("Don't know how to serialize {} object to a PODS".format(
                    field.type.__name__,
                ))

    @staticmethod
    def pods_to_value(value_expr, field):
        if field.type in PODS_TYPES:
            return value_expr
        elif field.type is RecursiveType or callable(getattr(field.type, 'from_pods', None)):
            return wrap_in_null_check(
                field.nullable,
                value_expr,
                SourceCodeTemplate(
                    '$cls.from_pods($value)',
                    cls=(
                        ExternalCodeInvocation(lambda: field.type, '')
                        if field.type is RecursiveType
                        else field.type
                    ),
                    value=value_expr,
                ),
            )
        else:
            unmarshalling_code = lookup_unmarshalling_code_for_type(field.type)
            if unmarshalling_code is not None:
                return wrap_in_null_check(
                    field.nullable,
                    value_expr,
                    ExternalCodeInvocation(unmarshalling_code, value_expr),
                )
            else:
                raise CannotBeSerializedToPods("Don't know how to load {} object from a PODS".format(
                    field.type.__name__,
                ))

#----------------------------------------------------------------------------------------------------------------------------------

class PodsMethodsForRecordTemplate(PodsMethodsTemplate):

    def __init__(self, class_name, fields):
        super(PodsMethodsForRecordTemplate, self).__init__()
        self.class_name = class_name
        self.fields = fields

    @property
    @serialization_exceptions_at_runtime
    def record_pods_impl(self):
        return Joiner('\n', 'pods = {}\n', '\nreturn pods', tuple(
            SourceCodeTemplate(
                '''
                if self.$field_id is not None:
                    pods[$key] = $value
                '''
                if field.nullable
                else 'pods[$key] = $value',
                field_id=field_id,
                key=repr(field_id),
                value=self.value_to_pods(
                    'self.{}'.format(field_id),
                    field,
                    needs_null_check=False,
                ),
            )
            for field_id, field in sorted(self.fields.items())
        ))

    @property
    @serialization_exceptions_at_runtime
    def from_pods_impl(self):
        return Joiner(', ', 'return cls(', ')', tuple(
            SourceCodeTemplate(
                '$key = $value',
                key=field_id,
                value=self.pods_to_value(
                    'pods.get({})'.format(repr(field_id)),
                    field,
                ),
            )
            for field_id, field in self.fields.items()
        ))

#----------------------------------------------------------------------------------------------------------------------------------

class PodsMethodsForSeqTemplate(PodsMethodsTemplate):

    def __init__(self, element_field):
        super(PodsMethodsForSeqTemplate, self).__init__()
        self.element_field = element_field

    @property
    @serialization_exceptions_at_runtime
    def record_pods_impl(self):
        return SourceCodeTemplate(
            'return [ $code_for_elem for elem in self ]',
            code_for_elem=self.value_to_pods('elem', self.element_field),
        )

    @property
    @serialization_exceptions_at_runtime
    def from_pods_impl(self):
        return SourceCodeTemplate(
            'return [ $code_for_elem for elem in pods ]',
            code_for_elem=self.pods_to_value('elem', self.element_field),
        )

#----------------------------------------------------------------------------------------------------------------------------------

class PodsMethodsForDictTemplate(PodsMethodsTemplate):

    def __init__(self, key_field, value_field):
        super(PodsMethodsForDictTemplate, self).__init__()
        self.key_field = key_field
        self.value_field = value_field

    @property
    @serialization_exceptions_at_runtime
    def record_pods_impl(self):
        return SourceCodeTemplate(
            'return { $code_for_key:$code_for_val for key, value in self.items() }',
            code_for_key=self.value_to_pods('key', self.key_field),
            code_for_val=self.value_to_pods('value', self.value_field),
        )

    @property
    @serialization_exceptions_at_runtime
    def from_pods_impl(self):
        return SourceCodeTemplate(
            'return { $code_for_key:$code_for_val for key, value in pods.items() }',
            code_for_key=self.pods_to_value('key', self.key_field),
            code_for_val=self.pods_to_value('value', self.value_field),
        )

#----------------------------------------------------------------------------------------------------------------------------------

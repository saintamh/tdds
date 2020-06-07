#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from itertools import chain
import re

# this module
from .basics import Field, FieldError, FieldValueError, FieldTypeError, FieldNotNullable, RecordsAreImmutable, \
    RecursiveType, compile_field
from .pods import PodsMethodsForRecordTemplate
from .unpickler import RecordRegistryMetaClass, RecordUnpickler
from .utils.codegen import ExternalCodeInvocation, ExternalValue, Joiner, SourceCodeTemplate, compile_expr
from .utils.compatibility import PY2, integer_types, native_string, string_types  # you're confused, pylint: disable=unused-import
from .utils.immutabledict import ImmutableDict

#----------------------------------------------------------------------------------------------------------------------------------
# the `Record' class is the main export of this module.

if PY2:
    builtin_module = '__builtin__'  # pylint: disable=invalid-name
else:
    builtin_module = 'builtins'  # pylint: disable=invalid-name


class RecordMetaClass(RecordRegistryMetaClass):
    def __new__(mcs, class_name, bases, attrib):
        attrib.pop('__qualname__', None)
        module = attrib.pop('__module__', None)
        is_codegen = (module == builtin_module)
        if bases == (object,) or is_codegen or Record not in bases:
            return type.__new__(mcs, class_name, bases, attrib)
        verbose = attrib.pop('_%s__verbose' % class_name, False)
        src_code_gen = RecordClassTemplate(class_name, bases, **attrib)
        cls = compile_expr(src_code_gen, class_name, verbose=verbose)
        if module is not None:
            setattr(cls, '__module__', module)
        mcs.register(class_name, cls)
        for field in cls.record_fields.values():
            field.set_recursive_type(cls)
        return cls


Record = RecordMetaClass(
    native_string('Record'),
    (object,),
    {}
)

#----------------------------------------------------------------------------------------------------------------------------------

# So this module uses `exec' on a string of Python code in order to generate the new classes.
#
# This is ugly, goes against all received standard practice, and makes this module rather hard to read, and therefore hard to
# modify, though I've tried to keep things as tidy and readable as possible. The reason for this is simply performance. The
# previous incarnation of this module (called "struct.py") used Python's great meta-programming facilities, and it ran quite slow.
# Using strings allows us to unroll loops over a record's fields, to use Python's native parameter system instead of having globs
# everywhere, to evaluate conditionals ("is this field nullable?") at class creation time rather than at every constructor
# invocation, etc etc. Some quick benchmarks show that this runs about 6x faster than struct.py.
#
# The bottom line is that this class has a huge ratio of how often it is used over how often it is modified, so I find it
# acceptable to make it harder to maintain for the sake of performance.

class RecordClassTemplate(SourceCodeTemplate):

    template = '''
        class $class_name($superclasses):
            __slots__ = $slots

            def __init__(self, $init_params):
                $super_call
                $field_checks
                $set_fields

            $properties
            $classmethods
            $staticmethods
            $instancemethods

            def __setattr__(self, attr, value):
                raise $RecordsAreImmutable("$class_name objects are immutable")
            def __delattr__(self, attr):
                raise $RecordsAreImmutable("$class_name objects are immutable")

            $pods_methods

            record_fields = $record_fields

            def record_derive(self, **kwargs):
                return self.__class__(**{
                    field_id: kwargs.get(field_id, getattr(self, field_id))
                    for field_id in $fields_including_super
                })

            $core_methods
    '''

    Record = Record
    RecordsAreImmutable = RecordsAreImmutable
    RecordUnpickler = RecordUnpickler

    def __init__(self, class_name, bases, **fields):
        super(RecordClassTemplate, self).__init__()
        self.class_name = class_name
        self.super_records = tuple(spr for spr in bases if spr is not Record and issubclass(spr, Record))
        self.super_fields = self._compile_super_fields(self.super_records, fields)
        self.property_defs, self.classmethod_defs, self.staticmethod_defs = (
            {
                field_id: fields.pop(field_id)
                for field_id, field in tuple(fields.items())
                if field.__class__ is special_type
            }
            for special_type in (property, classmethod, staticmethod)
        )
        self.instancemethod_defs = {
            field_id: fields.pop(field_id)
            for field_id, field in tuple(fields.items())
            if callable(field)
            and not isinstance(field, (type, Field))
        }
        self.fields = {
            field_id: compile_field(field)
            for field_id, field in fields.items()
        }
        self.fields_including_super = dict(chain(
            self.fields.items(),
            self.super_fields.items(),
        ))
        self.pods_methods = PodsMethodsForRecordTemplate(self.class_name, self.fields_including_super)

    @staticmethod
    def _compile_super_fields(super_records, fields):
        super_fields = {}
        for spr in super_records:
            for field_id, field in spr.record_fields.items():
                if field_id in super_fields:
                    raise TypeError('Multiple superclasses have a field called %r' % field_id)
                if field_id in fields:
                    raise TypeError("Can't override superclass field %r" % field_id)
                super_fields[field_id] = field
        return super_fields

    def _iter_fields_in_fixed_order(self, include_super=False):
        return sorted(
            dict.items(
                self.fields_including_super if include_super
                else self.fields
            ),
            key=lambda item: (item[1].nullable, item[0]),
        )

    def field_joiner_property(sep, prefix='', suffix='', include_super=False):  # not really a method, pylint: disable=no-self-argument
        return lambda raw_meth: property(
            lambda self: Joiner(sep, prefix, suffix, (
                raw_meth(self, field_id, field)
                for field_id, field in self._iter_fields_in_fixed_order(include_super)  # pylint: disable=protected-access
            ))
        )

    @field_joiner_property('', prefix='(', suffix=')')
    def slots(self, field_id, _field_unused):
        # NB trailing comma to ensure single value still a tuple
        return '{!r},'.format(field_id)

    @field_joiner_property('', prefix='(', suffix=')', include_super=True)
    def values_as_tuple(self, field_id, _field_unused):
        # NB trailing comma here too, for the same reason
        return 'self.{},'.format(field_id)

    @field_joiner_property(', ', include_super=True)
    def init_params(self, field_id, field):
        return '{}{}'.format(field_id, '=None' if field.nullable else '')

    @property
    def superclasses(self):
        return Joiner(', ', values=self.super_records + (Record,))

    @property
    def super_call(self):
        return 'super(%s, self).__init__(%s)' % (
            self.class_name,
            ', '.join(
                '%s=%s' % (field_id, field_id)
                for field_id in sorted(self.super_fields)
            ),
        )

    @field_joiner_property('\n')
    def field_checks(self, field_id, field):
        return FieldHandlingStmtsTemplate(
            field,
            field_id,
            description='{}.{}'.format(self.class_name, field_id)
        )

    @field_joiner_property('\n')
    def set_fields(self, field_id, _field_unused):
        # you can cheat past our fake immutability by using object.__setattr__, but don't tell anyone
        return 'object.__setattr__(self, "{0}", {0})'.format(field_id)

    @property
    def properties(self):
        if any(prop.fset is not None for prop in self.property_defs.values()):
            raise TypeError('record properties may not have an fset function')
        if any(prop.fdel is not None for prop in self.property_defs.values()):
            raise TypeError('record properties may not have an field function')
        return self._class_level_definitions(self.property_defs)

    @property
    def classmethods(self):
        return self._class_level_definitions(self.classmethod_defs)

    @property
    def staticmethods(self):
        return self._class_level_definitions(self.staticmethod_defs)

    @property
    def instancemethods(self):
        return self._class_level_definitions(self.instancemethod_defs)

    def _class_level_definitions(self, defs):
        return Joiner(sep='\n', values=(
            SourceCodeTemplate(
                '$field_id = $value',
                field_id=field_id,
                value=value,
            )
            for field_id, value in defs.items()
        ))

    @property
    def record_fields(self):
        return ImmutableDict(self.fields_including_super)

    @property
    def core_methods(self):
        return Joiner('\n\n', values=(
            code
            for name, code in self.iter_core_methods()
            if name not in self.instancemethod_defs
        ))

    def iter_core_methods(self):
        yield '__repr__', '''
            def __repr__(self):
                return "$class_name($repr_str)" % $values_as_tuple
        '''
        yield '__reduce__', '''
            def __reduce__(self):
                return ($RecordUnpickler(self.__class__.__name__), $values_as_tuple)
        '''
        yield '__key__', SourceCodeTemplate(
            '''
                def __key__(self):
                    return ($key)
            ''',
            key=Joiner(' ', values=(
                'self.{},'.format(field_id)
                for field_id, _ in self._iter_fields_in_fixed_order(include_super=True)
            )),
        )
        # eq, lt and hash defined on the basis of __key__
        yield '__eq__', '''
            def __eq__(self, other):
                return self.__key__() == other.__key__()
        '''
        yield '__lt__', '''
            def __lt__(self, other):
                return self.__key__() < other.__key__()
        '''
        yield '__hash__', '''
            def __hash__(self):
                return hash(self.__key__())
        '''
        # ne, le, gt and ge defined on the basis of eq and lt
        yield '__ne__', '''
            def __ne__(self, other):
                return not (self == other)
        '''
        yield '__le__', '''
            def __le__(self, other):
                return self < other or self == other
        '''
        yield '__gt__', '''
            def __gt__(self, other):
                return not (self < other or self == other)
        '''
        yield '__ge__', '''
            def __ge__(self, other):
                return not (self < other)
        '''

    @field_joiner_property(', ', include_super=True)
    def repr_str(self, field_id, _field_unused):
        return '{}=%r'.format(field_id)

#----------------------------------------------------------------------------------------------------------------------------------

class FieldHandlingStmtsTemplate(SourceCodeTemplate):
    """
    Given one field, this generates all constructor statements that relate to that one field: checks, default values, coercion,
    etc. This is inserted both into the constructor of the Record class, as well as in the constructor of the various collection
    types (seq_of etc), which also must check the value and type of their elements.
    """

    KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE = frozenset(
        string_types
        + integer_types
        + (float, bool)
    )

    template = '''
        $default_value
        $promote
        $coerce
        $null_check
        $value_check
        $type_check
    '''

    FieldError = FieldError
    FieldTypeError = FieldTypeError
    FieldValueError = FieldValueError
    FieldNotNullable = FieldNotNullable
    re = re
    integer_types = integer_types

    def __init__(self, field, variable_name, description):
        super(FieldHandlingStmtsTemplate, self).__init__()
        self.field = field
        self.variable_name = variable_name
        self.description = description
        self.field_type = field.type
        self.field_type_name = field.type.__name__

    @property
    def default_value(self):
        if self.field.nullable and self.field.default is not None:
            return '''
                if $variable_name is None:
                    $variable_name = $default_expr
            '''

    @property
    def default_expr(self):
        return ExternalValue(self.field.default)

    @property
    def promote(self):
        if self.field.type is float:
            # The only implicit promotion we allow among built-in scalar types is if you expected a float and you got an int
            # instead
            return '''
                if isinstance($variable_name, $integer_types):
                    $variable_name = float($variable_name)
            '''
        elif issubclass(self.field.type, Record):
            return '''
                if isinstance($variable_name, dict):
                    $variable_name = $field_type(**$variable_name)
            '''

    @property
    def coerce(self):
        if self.field.coerce is not None:
            return '$variable_name = $coerce_invocation'

    @property
    def coerce_invocation(self):
        return ExternalCodeInvocation(self.field.coerce, self.variable_name)

    @property
    def null_check(self):
        if not self.field.nullable and self.field.coerce not in self.KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE:
            return '''
                if $variable_name is None:
                    raise $FieldNotNullable("$description cannot be None")
            '''

    @property
    def value_check(self):
        if self.field.check is not None:
            return '''
                if $variable_name is not None and not $check_invocation:
                    raise $FieldValueError("$description: %r is not a valid value" % ($variable_name,))
            '''

    @property
    def check_invocation(self):
        return ExternalCodeInvocation(self.field.check, self.variable_name)

    @property
    def type_check(self):
        if self.field.coerce is not self.field.type:
            return '''
                if $not_null_and not $type_check_expr:
                    raise $FieldTypeError("$description should be of type $field_type_name, not %s (%r)" % (
                        $variable_name.__class__.__name__,
                        $variable_name,
                    ))
            '''

    @property
    def type_check_expr(self):
        if self.field.type is RecursiveType:
            # `self.field.type' will be imperatively modified after the class is compiled
            return ExternalCodeInvocation(
                lambda value: isinstance(value, self.field.type),
                '$variable_name',
            )
        else:
            return 'isinstance($variable_name, $field_type)'

    @property
    def not_null_and(self):
        if self.field.nullable:
            return '$variable_name is not None and '

#----------------------------------------------------------------------------------------------------------------------------------

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
from itertools import chain
import re

# this module
from .basics import Field, FieldError, FieldValueError, FieldTypeError, FieldNotNullable, RecordsAreImmutable, \
    RecursiveType, compile_field_def
from .pods import PodsMethodsForRecordTemplate
from .unpickler import RecordRegistryMetaClass, RecordUnpickler
from .utils.codegen import ExternalCodeInvocation, ExternalValue, Joiner, SourceCodeTemplate, compile_expr
from .utils.immutabledict import ImmutableDict

#----------------------------------------------------------------------------------------------------------------------------------
# the `Record' class is the main export of this module.

class RecordMetaClass(RecordRegistryMetaClass):
    def __new__(mcls, cls_name, bases, attrib):
        module = attrib.pop('__module__', None)
        is_codegen = (module == '__builtin__')
        if bases == (object,) or is_codegen or Record not in bases:
            return type.__new__(mcls, cls_name, bases, attrib)
        verbose = attrib.pop('_%s__verbose' % cls_name, False)
        src_code_gen = RecordClassTemplate(cls_name, bases, **attrib)
        cls = compile_expr(src_code_gen, cls_name, verbose=verbose)
        if module is not None:
            setattr(cls, '__module__', module)
        mcls.register(cls_name, cls)
        for fname,fdef in cls.record_fields.iteritems():
            fdef.set_recursive_type(cls)
        return cls

class Record(object):
    __metaclass__ = RecordMetaClass

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
        class $cls_name ($superclasses):
            __slots__ = $slots

            def __init__ (self, $init_params):
                $super_call
                $field_checks
                $set_fields

            $properties
            $classmethods
            $staticmethods
            $instancemethods

            def __setattr__ (self, attr, value):
                raise $RecordsAreImmutable ("$cls_name objects are immutable")
            def __delattr__ (self, attr):
                raise $RecordsAreImmutable ("$cls_name objects are immutable")

            $pods_methods

            record_fields = $record_fields

            def record_derive (self, **kwargs):
                return self.__class__ (**{
                    fname: kwargs.get (fname, getattr(self, fname))
                    for fname in $field_defs_incl_super
                })

            $core_methods
    '''

    Record = Record
    RecordsAreImmutable = RecordsAreImmutable
    RecordUnpickler = RecordUnpickler

    def __init__(self, cls_name, bases, **field_defs):
        self.cls_name = cls_name
        self.super_records = tuple(spr for spr in bases if spr is not Record and issubclass(spr, Record))
        self.super_field_defs = self._compile_super_field_defs(self.super_records, field_defs)
        self.prop_defs, self.classmethod_defs, self.staticmethod_defs = (
            {
                fname: field_defs.pop(fname)
                for fname,fdef in field_defs.items()
                if fdef.__class__ is special_type
            }
            for special_type in (property, classmethod, staticmethod)
        )
        self.instancemethod_defs = {
            fname: field_defs.pop(fname)
            for fname,fdef in field_defs.items()
            if callable(fdef)
            and not isinstance(fdef, (type, Field))
        }
        self.field_defs = {
            fname: compile_field_def(fdef)
            for fname,fdef in field_defs.items()
        }
        self.field_defs_incl_super = dict(chain(
            self.field_defs.items(),
            self.super_field_defs.items(),
        ))
        self.pods_methods = PodsMethodsForRecordTemplate(self.cls_name, self.field_defs_incl_super)

    @staticmethod
    def _compile_super_field_defs(super_records, field_defs):
        super_field_defs = {}
        for spr in super_records:
            for fname, fdef in spr.record_fields.items():
                if fname in super_field_defs:
                    raise TypeError("Multiple superclasses have a field called %r" % fname)
                if fname in field_defs:
                    raise TypeError("Can't override superclass field %r" % fname)
                super_field_defs[fname] = fdef
        return super_field_defs

    def field_joiner_property(sep, prefix='', suffix='', include_super=False):
        return lambda raw_meth: property(
            lambda self: Joiner(sep, prefix, suffix, (
                raw_meth(self, findex, fname, fdef)
                for findex,(fname,fdef) in enumerate(sorted(
                    dict.items(
                        self.field_defs_incl_super if include_super
                        else self.field_defs
                    ),
                    key = lambda (fname, fdef): (fdef.nullable, fname),
                ))
            ))
        )

    @field_joiner_property('', prefix='(', suffix=')')
    def slots(self, findex, fname, fdef):
        # NB trailing comma to ensure single val still a tuple
        return "{!r},".format(fname)

    @field_joiner_property('', prefix='(', suffix=')', include_super=True)
    def values_as_tuple(self, findex, fname, fdef):
        # NB trailing comma here too, for the same reason
        return 'self.{},'.format(fname)

    @field_joiner_property(', ', include_super=True)
    def init_params(self, findex, fname, fdef):
        return '{}{}'.format(fname, '=None' if fdef.nullable else '')

    @property
    def superclasses(self):
        return Joiner(', ', values=self.super_records + (Record,))

    @property
    def super_call(self):
        return 'super(%s,self).__init__(%s)' % (
            self.cls_name,
            ', '.join(
                '%s=%s' % (fname, fname)
                for fname in sorted(self.super_field_defs)
            ),
        )

    @field_joiner_property('\n')
    def field_checks(self, findex, fname, fdef):
        return FieldHandlingStmtsTemplate(
            fdef,
            fname,
            expr_descr='{}.{}'.format(self.cls_name,fname)
        )

    @field_joiner_property('\n')
    def set_fields(self, findex, fname, fdef):
        # you can cheat past our fake immutability by using object.__setattr__, but don't tell anyone
        return 'object.__setattr__ (self, "{0}", {0})'.format(fname)

    @property
    def properties(self):
        if any(prop.fset is not None for prop in self.prop_defs.values()):
            raise TypeError("record properties may not have an fset function")
        if any(prop.fdel is not None for prop in self.prop_defs.values()):
            raise TypeError("record properties may not have an fdef function")
        return self._class_level_definitions(self.prop_defs)

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
                '$fname = $value',
                fname = fname,
                value = value,
            )
            for fname, value in defs.items()
        ))

    @property
    def record_fields(self):
        return ImmutableDict(self.field_defs_incl_super)

    @property
    def core_methods(self):
        return ''.join(
            code
            for code in self.iter_core_methods()
            if re.search(r'def (\w+)', code).group(1) not in self.instancemethod_defs
        )

    def iter_core_methods(self):
        yield '''
            def __repr__ (self):
                return "$cls_name($repr_str)" % $values_as_tuple
        '''
        yield '''
            def __cmp__ (self, other):
                return $cmp_stmt
        '''
        yield '''
            def __hash__ (self):
                return $hash_expr
        '''
        yield '''
            def __reduce__ (self):
                return ($RecordUnpickler(self.__class__.__name__), $values_as_tuple)
        '''

    @field_joiner_property(', ', include_super=True)
    def repr_str(self, findex, fname, fdef):
        return '{}=%r'.format(fname)

    @field_joiner_property(' or ', prefix='1 if other is None else (', suffix=')', include_super=True)
    def cmp_stmt(self, findex, fname, fdef):
        return 'cmp(self.{0},getattr(other,{0!r},None))'.format(fname)

    @field_joiner_property(' + ', include_super=True)
    def hash_expr(self, findex, fname, fdef):
        return 'hash(self.{fname})*{mul}'.format(
            fname = fname,
            mul = 7**findex,
        )

#----------------------------------------------------------------------------------------------------------------------------------

class FieldHandlingStmtsTemplate(SourceCodeTemplate):
    """
    Given one field, this generates all constructor statements that relate to that one field: checks, default values, coercion,
    etc. This is inserted both into the constructor of the Record class, as well as in the constructor of the various collection
    types (seq_of etc), which also must check the value and type of their elements.
    """

    KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE = frozenset((
        int, long, float,
        str, unicode,
        bool,
    ))

    template = '''
        $default_value
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

    def __init__(self, fdef, var_name, expr_descr):
        self.fdef = fdef
        self.var_name = var_name
        self.expr_descr = expr_descr
        self.fdef_type = fdef.type
        self.fdef_type_name = fdef.type.__name__

    @property
    def default_value(self):
        if self.fdef.nullable and self.fdef.default is not None:
            return '''
                if $var_name is None:
                    $var_name = $default_expr
            '''

    @property
    def default_expr(self):
        return ExternalValue(self.fdef.default)

    @property
    def coerce(self):
        if self.fdef.coerce is not None:
            return '$var_name = $coerce_invocation'

    @property
    def coerce_invocation(self):
        return ExternalCodeInvocation(self.fdef.coerce, self.var_name)

    @property
    def null_check(self):
        if not self.fdef.nullable and self.fdef.coerce not in self.KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE:
            return '''
                if $var_name is None:
                    raise $FieldNotNullable ("$expr_descr cannot be None")
            '''

    @property
    def value_check(self):
        if self.fdef.check is not None:
            return '''
                if $var_name is not None and not $check_invocation:
                    raise $FieldValueError("$expr_descr: %r is not a valid value" % ($var_name,))
            '''

    @property
    def check_invocation(self):
        return ExternalCodeInvocation(self.fdef.check, self.var_name)

    @property
    def type_check(self):
        if self.fdef.coerce is not self.fdef.type:
            return '''
                if $not_null_and not $type_check_expr:
                    raise $FieldTypeError ("$expr_descr should be of type $fdef_type_name, not %s (%r)" % (
                        $var_name.__class__.__name__,
                        $var_name,
                    ))
            '''

    @property
    def type_check_expr(self):
        if self.fdef.type is RecursiveType:
            # `self.fdef.type' will be imperatively modified after the class is compiled
            return ExternalCodeInvocation(
                lambda value: isinstance(value, self.fdef.type),
                '$var_name',
            )
        else:
            return 'isinstance ($var_name, $fdef_type)'

    @property
    def not_null_and(self):
        if self.fdef.nullable:
            return '$var_name is not None and '

#----------------------------------------------------------------------------------------------------------------------------------

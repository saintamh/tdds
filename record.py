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
import re

# saintamh
from ..util.codegen import \
    ClassDefEvaluationNamespace, ExternalValue, SourceCodeTemplate, \
    compile_expr

# this module
from .basics import \
    Field, \
    FieldError, FieldValueError, FieldTypeError, FieldNotNullable, RecordsAreImmutable
from .json_decoder import \
    JsonDecoderMethodsForRecordTemplate
from .json_encoder import \
    JsonEncoderMethodsForRecordTemplate
from .unpickler import \
    RecordRegistryMetaclass, RecordUnpickler
from .utils import \
    ExternalCodeInvocation, Joiner, \
    compile_field_def

#----------------------------------------------------------------------------------------------------------------------------------
# the `record' function is the main export of this module. The `Field' data structure is also public.

def record (cls_name, **field_defs):
    verbose = field_defs.pop ('__verbose', False)
    src_code_gen = RecordClassTemplate (cls_name, **field_defs)
    return compile_expr (src_code_gen, cls_name, verbose=verbose)

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

class RecordClassTemplate (SourceCodeTemplate):

    template = '''
        class $cls_name (object):
            __metaclass__ = $RecordRegistryMetaclass
            __slots__ = $slots

            def __init__ (self, $init_params):
                $field_checks
                $set_fields

            def __setattr__ (self, attr, value):
                raise $RecordsAreImmutable ("$cls_name objects are immutable")
            def __delattr__ (self, attr):
                raise $RecordsAreImmutable ("$cls_name objects are immutable")

            $json_decoder_methods

            $json_encoder_methods

            # 2016-04-14 - added this for the JIRA client. Not sure yet it's the best approach. This can clash with field names.
            # Should we take the same approach as namedtuple and prefix all internal members with an underscore?
            record_fields = $slots

            # 2016-04-15 - same comment as above, I still reserve the option of changing the same here
            # Also should unroll the loop at compile time.
            def derive (self, **kwargs):
                return self.__class__ (**{
                    field: kwargs.get (field, getattr(self,field))
                    for field in $slots
                })

            def __repr__ (self):
                return "$cls_name ($repr_str)" % $values_as_tuple
            def __cmp__ (self, other):
                return $cmp_stmt
            def __hash__ (self):
                return $hash_expr

            def __reduce__ (self):
                return ($RecordUnpickler(self.__class__.__name__), $values_as_tuple)
    '''

    RecordsAreImmutable = RecordsAreImmutable
    RecordRegistryMetaclass = RecordRegistryMetaclass
    RecordUnpickler = RecordUnpickler

    def __init__ (self, cls_name, **field_defs):
        self.cls_name = cls_name
        self.field_defs = dict (
            (fname,compile_field_def(fdef))
            for fname,fdef in field_defs.items()
        )
        self.sorted_field_names = sorted (
            field_defs,
            key = lambda f: (self.field_defs[f].nullable, f),
        )
        self.json_decoder_methods = JsonDecoderMethodsForRecordTemplate (self.field_defs)
        self.json_encoder_methods = JsonEncoderMethodsForRecordTemplate (self.cls_name, self.field_defs)

    def field_joiner_property (sep, prefix='', suffix=''):
        return lambda raw_meth: property (
            lambda self: Joiner (sep, prefix, suffix, (
                raw_meth (self, i, f, self.field_defs[f])
                for i,f in enumerate(self.sorted_field_names)
            ))
        )

    @field_joiner_property ('', prefix='(', suffix=')')
    def slots (self, findex, fname, fdef):
        # NB trailing comma to ensure single val still a tuple
        return "{!r},".format(fname)

    @field_joiner_property ('', prefix='(', suffix=')')
    def values_as_tuple (self, findex, fname, fdef):
        # NB trailing comma here too, for the same reason
        return 'self.{},'.format (fname)

    @field_joiner_property (', ')
    def init_params (self, findex, fname, fdef):
        return '{}{}'.format (fname, '=None' if fdef.nullable else '')

    @field_joiner_property ('\n')
    def field_checks (self, findex, fname, fdef):
        return FieldHandlingStmtsTemplate (
            fdef,
            fname,
            expr_descr='{}.{}'.format(self.cls_name,fname)
        )

    @field_joiner_property ('\n')
    def set_fields (self, findex, fname, fdef):
        # you can cheat past our fake immutability by using object.__setattr__, but don't tell anyone
        return 'object.__setattr__ (self, "{0}", {0})'.format (fname)

    @field_joiner_property (', ')
    def repr_str (self, findex, fname, fdef):
        return '{}=%r'.format(fname)

    @field_joiner_property (' or ', prefix='1 if other is None else (', suffix=')')
    def cmp_stmt (self, findex, fname, fdef):
        return 'cmp(self.{0},other.{0})'.format(fname)

    @field_joiner_property (' + ')
    def hash_expr (self, findex, fname, fdef):
        return 'hash(self.{fname})*{mul}'.format (
            fname = fname,
            mul = 7**findex,
        )

#----------------------------------------------------------------------------------------------------------------------------------

class FieldHandlingStmtsTemplate (SourceCodeTemplate):
    """
    Given one field, this generates all constructor statements that relate to that one field: checks, default values, coercion,
    etc. This is inserted both into the constructor of the Record class, as well as in the constructor of the various collection
    types (seq_of etc), which also must check the value and type of their elements.
    """

    KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE = frozenset ((
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

    def __init__ (self, fdef, var_name, expr_descr):
        self.fdef = fdef
        self.var_name = var_name
        self.expr_descr = expr_descr
        self.fdef_type = fdef.type
        self.fdef_type_name = fdef.type.__name__

    @property
    def default_value (self):
        if self.fdef.nullable and self.fdef.default is not None:
            return '''
                if $var_name is None:
                    $var_name = $default_expr
            '''

    @property
    def default_expr (self):
        return ExternalValue(self.fdef.default)

    @property
    def coerce (self):
        if self.fdef.coerce is not None:
            return '$var_name = $coerce_invocation'

    @property
    def coerce_invocation (self):
        return ExternalCodeInvocation (self.fdef.coerce, self.var_name)

    @property
    def null_check (self):
        if not self.fdef.nullable and self.fdef.coerce not in self.KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE:
            return '''
                if $var_name is None:
                    raise $FieldNotNullable ("$expr_descr cannot be None")
            '''

    @property
    def value_check (self):
        if self.fdef.check is not None:
            return '''
                if not $check_invocation:
                    raise $FieldValueError("$expr_descr: %r is not a valid value" % ($var_name,))
            '''

    @property
    def check_invocation (self):
        return ExternalCodeInvocation (self.fdef.check, self.var_name)

    @property
    def type_check (self):
        if self.fdef.coerce is not self.fdef.type:
            return '''
                if $not_null_and not isinstance ($var_name, $fdef_type):
                    raise $FieldTypeError ("$expr_descr should be of type $fdef_type_name, not %s (%r)" % (
                        $var_name.__class__.__name__,
                        $var_name,
                    ))
            '''

    @property
    def not_null_and (self):
        if self.fdef.nullable:
            return '$var_name is not None and '

#----------------------------------------------------------------------------------------------------------------------------------

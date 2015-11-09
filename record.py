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
from functools import wraps
import re

# saintamh
from ..util.codegen import ClassDefEvaluationNamespace, SourceCodeGenerator, joiner

#----------------------------------------------------------------------------------------------------------------------------------
# the `record' function and the `Field' data structure are the two main exports of this module

def record (cls_name, **field_defs):
    verbose = field_defs.pop ('__verbose', False)
    src_code_gen = RecordClassGenerator (cls_name, **field_defs)
    cls = exec_cls_def (cls_name, src_code_gen, verbose=verbose)
    register_record_calls_for_unpickler (cls_name, cls)
    return cls

class Field (object):

    def __init__ (self, type, nullable=False, default=None, coerce=None, check=None):
        self.type = type
        self.nullable = nullable
        self.default = default
        self.coerce = coerce
        self.check = check
        self.ns = ClassDefEvaluationNamespace()

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

class FieldValueError (ValueError):
    pass

class FieldTypeError (ValueError):
    pass

class FieldNotNullable (FieldValueError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

# So this module uses `exec' on a string of Python code in order to generate the new classes.
#
# This is ugly, and makes this module rather hard to read, and hard to modify, though I've tried to keep things as tidy and
# readable as possible. The reason for this is simply performance. The previous incarnation of this module (called "struct.py")
# used Python's great meta-programming facilities, and it ran quite slow. Using strings allows us to unroll loops, use Python's
# native parameter system instead of having globs everywhere, evaluate conditionals ("is this field nullable?") at class creation
# time rather than at every constructor invocation, etc etc. Some quick benchmarks show that this runs about 6x faster than
# struct.py.
#
# The bottom line is that this class has a huge ratio of how often it is used over how often it is modified, so I find it
# acceptable to make it harder to maintain for the sake of performance.

class RecordClassGenerator (SourceCodeGenerator):

    template = '''
        class $cls_name (object):
            __slots__ = $slots

            def __init__ (self, $init_params):
                $field_checks
                $set_fields

            def __setattr__ (self, attr, value):
                raise RecordsAreImmutable ("$cls_name objects are immutable")
            def __delattr__ (self, attr):
                raise RecordsAreImmutable ("$cls_name objects are immutable")

            def json_struct (self):
                return {
                    $json_struct
                }

            def __repr__ (self):
                return "$cls_name ($repr_str)" % $values_as_tuple
            def __cmp__ (self, other):
                return $cmp_stmt
            def __hash__ (self):
                return $hash_expr

            def __reduce__ (self):
                return (RecordUnpickler("$cls_name"), $values_as_tuple)
    '''

    def __init__ (self, cls_name, **field_defs):
        super(RecordClassGenerator,self).__init__()
        field_defs = dict (
            (fname,compile_field_def(fdef))
            for fname,fdef in field_defs.items()
        )
        for fdef in field_defs.itervalues():
            self.ns.set (fdef.type.__name__, fdef.type)
            self.ns.update (fdef.ns)
        self.cls_name = cls_name
        self.field_defs = field_defs
        self.sorted_field_names = sorted (field_defs, key=lambda f: (field_defs[f].nullable, f))

    def field_joiner_property (sep, prefix='', suffix=''):
        # This little beauty transforms the raw method it decorates into one that returns a string obtained by mapping the raw
        # method to the sorted list of fields, and then joining the results together using the given separator.
        #
        # TODO: refactor this into something perhaps a little bit less dense?
        # 
        return lambda raw_meth: property (
            joiner(sep,prefix,suffix) (
                lambda self: (
                    str (raw_meth (self, i, f, self.field_defs[f]))
                    for i,f in enumerate(self.sorted_field_names)
                )
            )
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
        return str (
            FieldCodeGenerator (fdef, fname, expr_descr='{}.{}'.format(self.cls_name,fname))
        ).rstrip()

    @field_joiner_property ('\n')
    def set_fields (self, findex, fname, fdef):
        # you can cheat past our fake immutability by using object.__setattr__, but don't tell anyone
        return 'object.__setattr__ (self, "{0}", {0})'.format (fname)

    @field_joiner_property (', ')
    def repr_str (self, findex, fname, fdef):
        return '{}=%r'.format(fname)

    @field_joiner_property (' or ')
    def cmp_stmt (self, findex, fname, fdef):
        return 'cmp(self.{0},other.{0})'.format(fname)

    @field_joiner_property (' + ')
    def hash_expr (self, findex, fname, fdef):
        return 'hash(self.{fname})*{mul}'.format (
            fname = fname,
            mul = 7**findex,
        )

    @field_joiner_property (',\n')
    def json_struct (self, findex, fname, fdef):
        if hasattr (fdef.type, 'json_struct'):
            json_value_expr = 'self.{fname}.json_struct() if self.{fname} is not None else None'.format (fname=fname)
        else:
            json_value_expr = 'self.{fname}'.format (fname=fname)
        return '{fname!r}: {json_value_expr}'.format (
            fname = fname,
            json_value_expr = json_value_expr
        )

#----------------------------------------------------------------------------------------------------------------------------------

class FieldCodeGenerator (SourceCodeGenerator):
    """
    Given one field, this generates the statements to check its value and type. This is inserted into the constructor of any Record
    class, as well as in the constructor of the various collection types (seq_of etc), which also must check the value and type of
    their elements.
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

    def __init__ (self, fdef, value_expr, expr_descr):
        super(FieldCodeGenerator,self).__init__()
        self.fdef = fdef
        self.value_expr = value_expr
        self.expr_descr = expr_descr

    @property
    def default_value (self):
        if self.fdef.nullable and self.fdef.default is not None:
            return '''
                if $value_expr is None:,
                    $value_expr = $default_expr
            '''

    @property
    def default_expr (self):
        return SimpleExprCodeGenerator(fdef.default)

    @property
    def coerce (self):
        if self.fdef.coerce is not None:
            return '$value_expr = $coerce_invocation'

    @property
    def coerce_invocation (self):
        return compose_external_code_invocation_expr (self.ns, self.fdef.coerce, self.value_expr)

    @property
    def null_check (self):
        if not self.fdef.nullable and self.fdef.coerce not in self.KNOWN_COERCE_FUNCTIONS_THAT_NEVER_RETURN_NONE:
            return '''
                if $value_expr is None:
                    raise FieldNotNullable ("$expr_descr cannot be %r" % $value_expr)
            '''

    @property
    def value_check (self):
        if self.fdef.check is not None:
            return '''
                if not $check_invocation:
                    raise FieldValueError("%r is not a valid value for $expr_descr" % ($value_expr,))
            '''

    @property
    def check_invocation (self):
        return compose_external_code_invocation_expr (self.ns, self.fdef.check, self.value_expr)

    @property
    def type_check (self):
        if self.fdef.coerce is not self.fdef.type:
            return '''
                if $not_null_and not isinstance ($value_expr, $fdef_type_name):
                    raise FieldTypeError ("$expr_descr should be of type $fdef_type_name, not %s" % $value_expr_type_name)
            '''

    @property
    def fdef_type_name (self):
        return self.fdef.type.__name__

    @property
    def value_expr_type_name (self):
        return self.fdef.type.__name__

    @property
    def not_null_and (self):
        if self.fdef.nullable:
            return '$value_expr is not None and '

#----------------------------------------------------------------------------------------------------------------------------------
# collection fields (seq_of, dict_of, pair_of, set_of)

COLLECTION_TYPES = {}

class ImmutableDict (dict):
    def forbidden_operation (self, *args, **kwargs):
        raise TypeError ("ImmutableDict instances are read-only")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = forbidden_operation
    def __hash__ (self, _cache=[]):
        if not _cache:
            h = 0
            for key,val in sorted(self.iteritems()):
                h = h*2209 + hash(key)*47 + hash(val)
            _cache.append (h)
        return _cache[0]
    # We just defer to the built-in __cmp__ for dicts

def collection_builder (build_type):
    # A util to take some of the commonality out of seq_of, set_of and dict_of
    @wraps(build_type)
    def builder (*args, **kwargs):
        if 'coerce' in kwargs:
            # 2015-11-07 - This simplifies things greatly, but is it going to come and bite us in the butt some day?
            raise TypeError ("Can't specify a coercion function for sequences")
        coll_key = (build_type.__name__,args)
        coll_type = COLLECTION_TYPES.get(coll_key)
        if coll_type is None:
            COLLECTION_TYPES[coll_key] = coll_type = build_type (*args)
        return Field (
            coll_type,
            coerce = coll_type,
            **kwargs
        )
    return builder

@collection_builder
def seq_of (elem_type):
    class seq_type (tuple):
        def __init__ (self, values):
            super(seq_type,self).__init__ (values)
            for e in self:
                if not isinstance (e, elem_type):
                    raise FieldTypeError ('Element should be of type {}, not {}'.format (elem_type.__name__, e.__class__.__name__))
    seq_type.__name__ = '{}Sequence'.format (ucfirst(elem_type.__name__))
    return seq_type

@collection_builder
def pair_of (elem_type):
    class pair_type (tuple):
        def __init__ (self, values):
            super(pair_type,self).__init__ (values)
            if len(self) != 2:
                raise ValueError ('pairs must hold exactly 2 elements')
            for e in self:
                if not isinstance (e, elem_type):
                    raise FieldTypeError ('Element should be of type {}, not {}'.format (elem_type.__name__, e.__class__.__name__))
    pair_type.__name__ = '{}Pair'.format (ucfirst(elem_type.__name__))
    return pair_type

@collection_builder
def set_of (elem_type):
    class set_type (frozenset):
        def __init__ (self, values):
            super(set_type,self).__init__ (values)
            for e in self:
                if not isinstance (e, elem_type):
                    raise FieldTypeError ('Element should be of type {}, not {}'.format (elem_type.__name__, e.__class__.__name__))
        def json_struct (self):
            return tuple(self)
    set_type.__name__ = '{}Set'.format (ucfirst(elem_type.__name__))
    return set_type

@collection_builder
def dict_of (key_type, val_type, **kwargs):
    class dict_type (ImmutableDict):
        def __init__ (self, *args, **kwargs):
            super(dict_type,self).__init__ (*args, **kwargs)
            for k,v in self.iteritems():
                if not isinstance (k, key_type):
                    raise FieldTypeError ('Key should be of type {}, not {}'.format (key_type.__name__, k.__class__.__name__))
                if not isinstance (v, val_type):
                    raise FieldTypeError ('Value should be of type {}, not {}'.format (val_type.__name__, v.__class__.__name__))
    dict_type.__name__ = '{}{}Dictionary'.format (ucfirst(key_type.__name__), ucfirst(val_type.__name__))
    return dict_type

#----------------------------------------------------------------------------------------------------------------------------------
# utilities for common scalar fields

def value_check (name, check):
    def func (fdef):
        fdef = compile_field_def(fdef)
        if fdef.check is not None:
            raise Exception ("I haven't figured out how to chain value checks yet")
        return fdef.derive (check=check)
    func.__name__ = name
    return func

nonnegative = value_check ('nonnegative', '{} >= 0')
strictly_positive = value_check ('strictly_positive', '{} > 0')

def regex_check (name, char_def):
    def func (n=None):
        multiplier = ('{{{{%d}}}}' % n) if n is not None else '*'
        fdef = Field (
            type = str,
            check = "re.search(r'^[%s]%s$',{})" % (char_def, multiplier),
        )
        fdef.ns.add (re)
        return fdef
    func.__name__ = name
    return func

uppercase_letters = regex_check ('uppercase_letters', 'A-Z')
uppercase_wchars  = regex_check ('uppercase_wchars', '[A-Z0-9_]')
uppercase_hex     = regex_check ('uppercase_hex', '0-9A-F')

lowercase_letters = regex_check ('lowercase_letters', 'a-z')
lowercase_wchars  = regex_check ('lowercase_wchars', '[a-z0-9_]')
lowercase_hex     = regex_check ('lowercase_hex', '0-9a-f')

digits_str        = regex_check ('digits_str', '0-9')

absolute_http_url = Field (
    type = str,
    check = "re.search(r'^https?://.{1,2000}$',{})"
)

#----------------------------------------------------------------------------------------------------------------------------------
# other field def utils

def one_of (*values):
    if len(values) == 0:
        raise ValueError ('one_of requires arguments')
    type = values[0].__class__
    for v in values[1:]:
        if v.__class__ is not type:
            raise ValueError ("All arguments to one_of should be of the same type (%s is not %s)" % (
                type.__name__,
                v.__class__.__name__,
            ))
    values = frozenset (values)
    return Field (
        type = type,
        check = values.__contains__,
    )

def nullable (fdef):
    return compile_field_def(fdef).derive (
        nullable = True,
    )

#----------------------------------------------------------------------------------------------------------------------------------
# code-generation utils (private)

def compile_field_def (fdef):
    if isinstance(fdef,Field):
        return fdef
    else:
        return Field(fdef)

def compose_external_code_invocation_expr (ns, code_ref, param_expr):
    if code_ref is None:
        return param_expr
    elif isinstance (code_ref, basestring):
        return '({})'.format (code_ref.format(param_expr))
    elif hasattr (code_ref, '__call__'):
        return '{coerce_sym}({param_expr})'.format (
            param_expr = param_expr,
            coerce_sym = ns.add (code_ref),
        )
    else:
        raise TypeError (repr(code_ref))
            
def exec_cls_def (cls_name, src_code_gen, verbose=False):
    src_code_str = str(src_code_gen)
    if verbose:
        print src_code_str + '\n'
    for cls in (RecordsAreImmutable,FieldValueError,FieldTypeError,FieldNotNullable,RecordUnpickler):
        src_code_gen.ns.set (cls.__name__, cls)
    ns_dict = src_code_gen.ns.asdict()
    exec src_code_str in ns_dict
    return ns_dict[cls_name]

#----------------------------------------------------------------------------------------------------------------------------------

# Because Records are dynamically created classes that are compiled within a function, 'pickle' cannot find the class definition by
# name alone. For this reason we need to keep a register here of all Record classes that have been created, indexed by name.
#
# This is rather hacky, and has a few implications: you shouldn't create millions of record classes, as they'll all be referenced
# here, and you can't create two record classes with the same name. The latter could come back to bite me some day. I'm not sure
# what I'll do then.

ALL_RECORDS = {}

def register_record_calls_for_unpickler (cls_name, cls):
    ALL_RECORDS[cls_name] = cls

class RecordUnpickler (object):
    def __init__ (self, cls_name):
        self.cls_name = cls_name
    def __call__ (self, *values):
        return ALL_RECORDS[self.cls_name](*values)

#----------------------------------------------------------------------------------------------------------------------------------
# misc utils

def ucfirst (s):
    # like s.capitalize(), but only affects the 1st letter, leaves the rest untouched
    if s[0] == s[0].upper():
        return s
    else:
        return s[:1].upper() + s[1:]

#----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    g = RecordClassGenerator('Test', x=int, y=Field(type=int, check='{} >= x'), label=nullable(unicode))
    print g

#----------------------------------------------------------------------------------------------------------------------------------

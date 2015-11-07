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
import re

#----------------------------------------------------------------------------------------------------------------------------------

# So this module uses `exec' on a string of Python code in order to generate the new classes.
#
# This is ugly, and makes this module rather hard to read, and hard to modify, though I've tried to keep things as tidy and
# readable as possible. The reason for this is simply performance. The previous incarnation of this module (called "struct.py")
# used Python's great meta-programming facilities, and it ran quite slow. Using strings allows us to unroll loops, use Python's
# native parameter system instead of having globs everywhere, evaluate conditionals ("is this field nullable?") at class creation
# time rather than at every constructor invocation, etc etc.
#
# The bottom line is that this class has a huge ratio of how often it is used over how often it is modified, so I find it
# acceptable to make it harder to maintain for the sake of performance.

cls_def_template = '''\
class {cls_name} (object):
    __slots__ = {field_names!r}

    def __init__ (self, {init_params}):
        {init_body}

    def __setattr__ (self, attr, value):
        raise RecordsAreImmutable ("{cls_name} objects are immutable")
    def __delattr__ (self, attr):
        raise RecordsAreImmutable ("{cls_name} objects are immutable")

    def json_struct (self):
        return {{{json_struct}}}

    def __repr__ (self):
        return "{cls_name} ({repr_str})" % {values_as_tuple}
    def __cmp__ (self, other):
        return {cmp_stmt}

    def __reduce__ (self):
        return (RecordUnpickler("{cls_name}"), {values_as_tuple})
'''

#----------------------------------------------------------------------------------------------------------------------------------

class Field (object):
    def __init__ (self, type, nullable=False, default=None, coerce=None, check=None):
        self.type = type
        self.nullable = nullable
        self.default = default
        self.coerce = coerce
        self.check = check
    def derive (self, nullable=None, default=None):
        return self.__class__ (
            type = self.type,
            nullable = self.nullable if nullable is None else nullable,
            default = self.default if default is None else default,
        )
    def is_none_expr (self, value_expr):
        return '{0} is None'.format (value_expr)

#----------------------------------------------------------------------------------------------------------------------------------
# other public classes & utils

class RecordsAreImmutable (TypeError):
    pass

class FieldCheckFailed (ValueError):
    pass

class FieldIsNotNullable (ValueError):
    pass

def nullable (fdef):
    return compile_field_def(fdef).derive (nullable=True)

#----------------------------------------------------------------------------------------------------------------------------------

class ClassDefEvaluationNamespace (object):
    def __init__ (self):
        self.ns = {}
    def add (self, value):
        for symbol in (
                getattr (value, '__name__', None),
                '_cls_def_symbol_{:d}'.format (len(self.ns)),
                ):
            if symbol is None or not re.search (r'^(?!\d)\w+$', symbol):
                continue
            elif self.ns.get(symbol) is value:
                return symbol
            elif symbol not in self.ns:
                self.ns[symbol] = value
                return symbol
            # else continue
        raise Exception ("Should never get here")
    def set (self, symbol, value):
        assert symbol not in self.ns or self.ns[symbol] is value, \
            (symbol, self.ns[symbol], value)
        self.ns[symbol] = value
    def asdict (self):
        return dict(self.ns)

def compile_field_defs (field_defs):
    for fname,fdef in field_defs.items():
        field_defs[fname] = compile_field_def(fdef)

def compile_field_def (fdef):
    if isinstance(fdef,Field):
        return fdef
    else:
        return Field(fdef)

def compose_external_code_invocation_expr (ns, code_ref, param_expr):
    if isinstance (code_ref, basestring):
        return '({})'.format (code_ref.format(param_expr))
    elif hasattr (code_ref, '__call__'):
        return '{coerce_sym}({param_expr})'.format (
            param_expr = param_expr,
            coerce_sym = ns.add (code_ref),
        )
    else:
        raise TypeError (repr(code_ref))

def compose_coercion_stmts (ns, fname, fdef):
    yield '{fname} = {invoke}'.format (
        fname = fname,
        invoke = compose_external_code_invocation_expr (ns, fdef.coerce, fname)
    )

def compose_check_stmts (ns, cls_name, fname, fdef):
    yield 'if not {check}:'.format (
        check = compose_external_code_invocation_expr (ns, fdef.check, fname),
    )
    yield '    raise FieldCheckFailed("%r is not a valid value for {cls_name}.{fname}" % ({fname},))'.format (
        fname = fname,
        cls_name = cls_name,
    )

def compose_constructor_stmts (ns, cls_name, fname, fdef):
    lines = []
    if fdef.nullable:
        lines.extend ((
            'if {is_none}:',
            '    {fname} = {fdef.default!r}',
        ))
    if fdef.coerce is not None:
        lines.extend (compose_coercion_stmts (ns, fname, fdef))
    if not fdef.nullable:
        lines.extend ((
            'if {is_none}:',
            '    raise FieldIsNotNullable ("{cls_name}.{fname} cannot be %r" % {fname})',
        ))
    if fdef.check is not None:
        lines.extend (compose_check_stmts (ns, cls_name, fname, fdef))
    lines.extend ((
        'if {not_null_and_}not isinstance ({fname}, {fdef.type.__name__}):',
        '    raise TypeError ("{cls_name}.{fname} should be of type {fdef.type.__name__}, not %s" % {fname}.__class__.__name__)',
    ))
    # you can cheat past our fake immutability by using object.__setattr__
    lines.append ('object.__setattr__ (self, "{fname}", {fname})')
    return '\n'.join (
        '        ' + l.format (
            is_none = fdef.is_none_expr (fname),
            not_null_and_ = '{fname} is not None and '.format(fname=fname) if fdef.nullable else '',
            fname = fname,
            fdef = fdef,
            cls_name = cls_name,
        )
        for l in lines
    )

def compose_json_key_value_pair (fname, fdef):
    if hasattr (fdef.type, 'json_struct'):
        json_value_expr = 'self.{fname}.json_struct() if self.{fname} is not None else None'.format (fname=fname)
    else:
        json_value_expr = 'self.{fname}'.format (fname=fname)
    return '{fname!r}: {json_value_expr}'.format (
        fname = fname,
        json_value_expr = json_value_expr
    )
            
def exec_cls_def (cls_name, field_defs, ns, cls_def_str, verbose=False):
    if verbose:
        print cls_def_str
    for fdef in field_defs.itervalues():
        ns.set (fdef.type.__name__, fdef.type)
    for cls in (RecordsAreImmutable,FieldCheckFailed,FieldIsNotNullable,RecordUnpickler):
        ns.set (cls.__name__, cls)
    ns_dict = ns.asdict()
    exec cls_def_str in ns_dict
    return ns_dict[cls_name]

#----------------------------------------------------------------------------------------------------------------------------------

def record (cls_name, **field_defs):
    __verbose = field_defs.pop ('__verbose', False)
    compile_field_defs (field_defs)
    sorted_field_names = tuple (sorted (field_defs, key = lambda f: (
        0 if not field_defs[f].nullable else 1,
        f
    )))
    ns = ClassDefEvaluationNamespace()
    cls_def_str = cls_def_template.format (
        cls_name = cls_name,
        field_names = sorted_field_names,
        init_params = ', '.join ('{}{}'.format (f, '=None' if field_defs[f].nullable else '') for f in sorted_field_names),
        init_body = '\n'.join (compose_constructor_stmts(ns,cls_name,f,field_defs[f]) for f in sorted_field_names).lstrip(),
        repr_str = ', '.join ('{}=%r'.format(f) for f in sorted_field_names),
        values_as_tuple = '({})'.format (
            # NB trailing comma to ensure single val still a tuple
            ''.join (map ('self.{},'.format, sorted_field_names))
        ),
        cmp_stmt = ' or '.join ('cmp(self.{0},other.{0})'.format(f) for f in sorted_field_names),
        json_struct = ', '.join (compose_json_key_value_pair(f,field_defs[f]) for f in sorted_field_names),
    )
    cls = exec_cls_def (cls_name, field_defs, ns, cls_def_str, verbose=__verbose)
    register_record_calls_for_unpickler (cls_name, cls)
    return cls

#----------------------------------------------------------------------------------------------------------------------------------

# Because Records are dynamically created classes that are compiled within a function, 'pickle' cannot find the class definition by
# name alone. For this reason we need to keep a register here of all Record classes that have been created, indexed by name. This
# is rather hacky, and has a few implications: you shouldn't create millions of record classes, as they'll all be referenced here,
# and you can't create two record classes with the same name. The latter could come back to bite me some day. I'm not sure what
# I'll do then.

ALL_RECORDS = {}

def register_record_calls_for_unpickler (cls_name, cls):
    ALL_RECORDS[cls_name] = cls

class RecordUnpickler (object):
    def __init__ (self, cls_name):
        self.cls_name = cls_name
    def __call__ (self, *values):
        return ALL_RECORDS[self.cls_name](*values)

#----------------------------------------------------------------------------------------------------------------------------------

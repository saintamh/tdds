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
from types import MethodType

# saintamh
from ..util.codegen import SourceCodeGenerator

# this module
from .basics import Field

#----------------------------------------------------------------------------------------------------------------------------------
# code-generation utils (private)

def compile_field_def(fdef, **kwargs):
    if isinstance(fdef,Field):
        if kwargs:
            return fdef.derive(**kwargs)
        else:
            return fdef
    else:
        assert not kwargs, (fdef, kwargs)
        return Field(fdef)

class ExternalCodeInvocation(SourceCodeGenerator):
    """
    This somewhat clumsy class is for encapsulating user-supplied code refs to be inserted into the compiled class. This was
    originally designed specifically for the `coerce' and `check' functions that can be attached to a `Field'. The code ref
    can be given as a string of Python code, as a SourceCodeGenerator (which creates such a string), or as a callable. If a string,
    the code ref must contain exactly one occurence of '{}', which will be used to inject the parameter expression in.

    `param_expr' is a string of Python code that evaluates to the expression passed to the code ref. It is not resolved within this
    class, and we don't run checks on it. It's up to the caller to ensure that that expression is valid within the context where
    the expanded string of code will be evaluated.
    """

    def __init__(self, code_ref, param_expr):
        self.code_ref = code_ref
        self.param_expr = param_expr

    def expand(self, ns):
        code_ref = self.code_ref
        if isinstance(code_ref, SourceCodeGenerator):
            code_ref = code_ref.expand(ns)
        if isinstance(code_ref, basestring):
            if not re.search(
                    # Avert your eyes. This checks that there is one and only one '{}' in the string. Escaped {{ and }} are allowed
                    r'^(?:[^\{\}]|\{\{|\}\})*\{\}(?:[^\{\}]|\{\{|\}\})*$',
                    code_ref,
                    ):
                raise ValueError(code_ref)
            return '({})'.format(code_ref.format(self.param_expr))
        elif hasattr(code_ref, '__call__'):
            return '{coerce_sym}({param_expr})'.format(
                coerce_sym = ns.intern(code_ref),
                param_expr = self.param_expr,
            )
        else:
            raise TypeError(repr(code_ref))

class Joiner(SourceCodeGenerator):

    def __init__(self, sep, prefix='', suffix='', values=None):
        self.sep = sep
        self.prefix = prefix
        self.suffix = suffix
        self.values = values

    def expand(self, ns):
        return '{prefix}{body}{suffix}'.format(
            prefix = self.prefix,
            suffix = self.suffix,
            body = self.sep.join(self.code_string(ns,v) for v in self.values),
        )

#----------------------------------------------------------------------------------------------------------------------------------

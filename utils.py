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
from ..util.codegen import SourceCodeGenerator

# this module
from .basics import Field

#----------------------------------------------------------------------------------------------------------------------------------
# code-generation utils (private)

def compile_field_def (fdef, **kwargs):
    if isinstance(fdef,Field):
        if kwargs:
            return fdef.derive (**kwargs)
        else:
            return fdef
    else:
        return Field(fdef)

class ExternalCodeInvocation (SourceCodeGenerator):

    def __init__ (self, code_ref, *param_exprs):
        self.code_ref = code_ref
        self.param_exprs = param_exprs

    def expand (self, ns):
        if isinstance (self.code_ref, basestring):
            assert len(self.param_exprs) == 1, self.param_exprs
            if not re.search (
                    # Avert your eyes. This checks that there is one and only one '{}' in the string. Escaped {{ and }} are allowed
                    r'^(?:[^\{\}]|\{\{|\}\})*\{\}(?:[^\{\}]|\{\{|\}\})*$',
                    self.code_ref,
                    ):
                raise ValueError (self.code_ref)
            return '({})'.format (self.code_ref.format (self.param_exprs[0]))
        elif hasattr (self.code_ref, '__call__'):
            return '{coerce_sym}({params})'.format (
                coerce_sym = ns.intern (self.code_ref),
                params = Joiner (', ', values=self.param_exprs).expand(ns),
            )
        else:
            raise TypeError (repr(self.code_ref))

class Joiner (SourceCodeGenerator):

    def __init__ (self, sep, prefix='', suffix='', values=None):
        self.sep = sep
        self.prefix = prefix
        self.suffix = suffix
        self.values = values

    def expand (self, ns):
        return '{prefix}{body}{suffix}'.format (
            prefix = self.prefix,
            suffix = self.suffix,
            body = self.sep.join (self.code_string(ns,v) for v in self.values),
        )

#----------------------------------------------------------------------------------------------------------------------------------

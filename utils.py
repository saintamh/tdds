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

def compile_field_def (fdef):
    if isinstance(fdef,Field):
        return fdef
    else:
        return Field(fdef)

class ExternalCodeInvocation (SourceCodeGenerator):

    def __init__ (self, code_ref, param_expr):
        self.code_ref = code_ref
        self.param_expr = param_expr

    def expand (self, ns):
        if isinstance (self.code_ref, basestring):
            if not re.search (
                    # Avert your eyes. This checks that there is one and only one '{}' in the string. Escaped {{ and }} are allowed
                    r'^(?:[^\{\}]|\{\{|\}\})*\{\}(?:[^\{\}]|\{\{|\}\})*$',
                    self.code_ref,
                    ):
                raise ValueError (self.code_ref)
            return '({})'.format (self.code_ref.format (self.param_expr))
        elif hasattr (self.code_ref, '__call__'):
            return '{coerce_sym}({param_expr})'.format (
                coerce_sym = ns.intern (self.code_ref),
                param_expr = self.param_expr,
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
            body = self.sep.join (
                # There's a similar isinstance check in SourceCodeTemplate.lookup. Feels like I'm missing some elegant way of
                # unifying these two.
                v.expand(ns) if isinstance(v,SourceCodeGenerator) else str(v)
                for v in self.values
            ),
        )

#----------------------------------------------------------------------------------------------------------------------------------

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A toolset for building and evaluating strings of Python code.
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from itertools import count
import logging
import re

from .compatibility import python_builtins, string_types

#----------------------------------------------------------------------------------------------------------------------------------

class SourceCodeGenerator(object):

    # FIXME - 2015-11-11 - I've been completely ignoring the issue of unicode strings as source code. Does `exec' work with
    # unicode strings? Or do you pass a str that optionally contains an encoding declaration in it, like this file does?

    def expand(self, ns):
        raise NotImplementedError('expand')

    def code_string(self, ns, value):
        if value is None:
            subst_str = ''
        elif isinstance(value, string_types):
            # 2015-11-11 - see confusion in the comment above
            subst_str = value
        else:
            if not isinstance(value, SourceCodeGenerator):
                value = ExternalValue(value)
            subst_str = value.expand(ns)
        return subst_str

class ExternalValue(SourceCodeGenerator):
    def __init__(self, value):
        self.value = value
    def expand(self, ns):
        return ns.intern(self.value)

class UnknownVariableInTemplate(ValueError):
    def __init__(self, host, variable_name, template_str):
        super(UnknownVariableInTemplate, self).__init__('{}\n\n{!r} not found in {!r}'.format(
            template_str,
            variable_name,
            host,
        ))

#----------------------------------------------------------------------------------------------------------------------------------

class SourceCodeTemplate(SourceCodeGenerator):
    """
    A single template for source code, held as a string, as well as a mechanism for substitutions within the code.

    The template can contain a number of $variables. These will be substituted when the template is expanded. The value that each
    variable is replaced with comes from the SourceCodeTemplate object's property having the same name as the variable.
    """

    template = NotImplemented

    def __init__(self, template=None, **vars):
        if template is not None:
            self.template = template
        for k, v in vars.items():
            setattr(self, k, v)

    def lookup(self, variable_name, ns):
        not_found = object()
        variable_value = getattr(self, variable_name, not_found)
        if variable_value is not_found:
            raise UnknownVariableInTemplate(self, variable_name, self.template)
        return self.code_string(ns, variable_value)

    def replace_whole_lines(self, src, ns, expanded_vars=frozenset()):
        """
        When a variable appears on its own on a line in the template, the substitution happens somewhat differently: if the string
        that the variable resolves to is a multiline piece of code, each line will be indented to be at the same level as the
        variable originally appeared within the template.
        """
        def whole_line_subst(indent, variable_name):
            if variable_name not in expanded_vars:
                subst = shift_left(self.lookup(variable_name, ns))
                subst = shift_right(indent, subst).lstrip()
                subst = subst and (indent + subst + '\n')
                subst = self.replace_whole_lines(subst, ns, expanded_vars | set([variable_name]))
                return subst
            else:
                return '$' + variable_name
        return re.sub(
            r'(?<![^\n])(\ *)\$(?:(\w+)|\{(\w+)\})\ *(?:$|\n)',
            lambda m: whole_line_subst(
                m.group(1),
                m.group(2) or m.group(3),
            ),
            src
        )

    def replace_all_variables(self, src, ns, expanded_vars=frozenset()):
        def simple_subst(variable_name):
            if variable_name not in expanded_vars:
                subst = self.lookup(variable_name, ns)
                assert '\n' not in subst, (src, variable_name, subst)
                subst = self.replace_all_variables(subst, ns, expanded_vars | set([variable_name]))
                return subst
            else:
                return '$' + variable_name
        return re.sub(
            r'\$(?:(\w+)|\{(\w+)\})',
            lambda m: simple_subst(m.group(1) or m.group(2)),
            src,
        )

    def expand(self, ns):
        src = shift_left(self.template)
        src = self.replace_whole_lines(src, ns)
        src = self.replace_all_variables(src, ns)
        return src

#----------------------------------------------------------------------------------------------------------------------------------

class ClassDefEvaluationNamespace(object):
    """
    When evaluating a piece of Python code from a string there will often be values that you have available at compile time and
    that you want available within the compiled code. In order to do that you need to give them a unique name, use that unique name
    within the compiled code, and pass the value to the `exec' statement in the namespace directory, keyed under that unique name.
    Here we keep track of such values.
    """

    def __init__(self):
        self.name_by_value_id = {}
        self.value_by_name = {}

    def intern(self, value):
        if getattr(python_builtins, getattr(value, '__name__', ''), None) is value:
            # No need to alias 'int' etc
            return value.__name__
        value_id = id(value)
        name = self.name_by_value_id.get(value_id)
        if name is None:
            basename = getattr(value, '__name__', '!')
            if not re.search(r'^(?!\d)\w+$', basename):
                basename = 'obj'
            basename = 'intern___' + basename
            for i in count():
                name = '{:s}_{:d}'.format(basename, i)
                if name not in self.value_by_name:
                    self.name_by_value_id[value_id] = name
                    self.value_by_name[name] = value
                    break
                if i > 1000000:
                    raise Exception('wat')
        return name

    def as_dict(self):
        return dict(self.value_by_name)

#----------------------------------------------------------------------------------------------------------------------------------
# compilation functions

def compile_template(template, verbose=False):
    ns = ClassDefEvaluationNamespace()
    src_code_str = template.expand(ns)
    if verbose:
        logging.debug('\n%s', src_code_str)
    ns_dict = ns.as_dict()
    try:
        eval(  # yes, pylint: disable=eval-used
            compile(src_code_str, '<string>', 'exec'),
            ns_dict,
            ns_dict,
        )
    except SyntaxError:
        logging.error(src_code_str)
        raise
    return ns_dict

def compile_expr(template, expr_name=None, verbose=False):
    if expr_name is None:
        m = re.search(r'^\s*(?:class|def)\s+(\w+)', template)
        if m is None:
            raise ValueError('expr_name not specified and not found in template')
        expr_name = m.group(1)
    ns_dict = compile_template(template, verbose=verbose)
    return ns_dict[expr_name]

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def shift_left(src):
    """
    Given a piece of Python code as a string, shift it all left (i.e. deindent it) as far as possible. Assumes that all lines are
    at least as far indented as the 1st (non-empty) line.
    """
    assert '\t' not in src, repr(src)
    src = re.sub(r'^\ *\n', '', src)
    src = src.rstrip()
    indent = re.search(r'^(\ *)', src).group(1)
    parts = []
    for line in src.split('\n'):
        if line.startswith(indent):
            parts.append(line[len(indent):])
        elif re.search(r'^\s*$', line):
            parts.append(line)
        else:
            logging.error(src)
            raise ValueError('code block must start with top-level indent (%r)' % line)
    return '\n'.join(parts)

def shift_right(indent, src):
    """
    Shifts the given piece of Python code right by the given indent.
    """
    assert '\t' not in src, repr(src)
    return re.sub(r'^', indent, src, flags=re.M)

#----------------------------------------------------------------------------------------------------------------------------------
# code-generation utils (private)

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
        if isinstance(code_ref, string_types):
            if not re.search(
                    # Avert your eyes. This checks that there is one and only one '{}' in the string. Escaped {{ and }} are allowed
                    r'^(?:[^\{\}]|\{\{|\}\})*\{\}(?:[^\{\}]|\{\{|\}\})*$',
                    code_ref,
            ):
                raise ValueError(code_ref)
            return '({})'.format(code_ref.format(self.param_expr))
        elif hasattr(code_ref, '__call__'):
            return '{coerce_sym}({param_expr})'.format(
                coerce_sym=ns.intern(code_ref),
                param_expr=self.param_expr,
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
            prefix=self.prefix,
            suffix=self.suffix,
            body=self.sep.join(shift_left(self.code_string(ns, v)) for v in self.values),
        )

#----------------------------------------------------------------------------------------------------------------------------------

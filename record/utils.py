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
from functools import wraps
import re
from types import MethodType

# saintamh
from ..util.codegen import SourceCodeGenerator
from ..util.lang import Undef
from ..util.iterables import first

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
# builder utils (public)

class BuilderMetaClass(type):
    """
    If a Builder class for a record class R defines a method called "x_and_y", and "x" and "y" are both fields of R, then new
    methods named "x" and "y" are automatically created, and when either is called, it will call "x_and_y", cache the result (on
    `self'), and return the corresponding value.
    """

    def __new__(mcls, name, bases, attrib):
        return type.__new__(mcls, name, bases, dict(mcls._expand_multiple_field_methods(bases, attrib)))

    @classmethod
    def _expand_multiple_field_methods(mcls, bases, attrib):
        record_cls = first(getattr(b, 'record_cls', None) for b in bases)
        for key, value in attrib.iteritems():
            if record_cls is not None \
                    and '_and_' in key \
                    and callable(value) \
                    and all(f in record_cls.record_fields for f in key.split('_and_')):
                memoized_method = mcls._memoize(key, value)
                for i,f in enumerate(key.split('_and_')):
                    if f in attrib:
                        raise Exception("Can't have both %r and %r" % (key, f))
                    yield f, mcls._single_field_method(memoized_method, i)
            else:
                yield key, value

    @staticmethod
    def _single_field_method(memoized_method, field_index):
        return lambda self: memoized_method(self)[field_index]

    @staticmethod
    def _memoize(name, method):
        cache_attribute = '__%s_cache' % name
        @wraps(method)
        def wrapped(self, *args, **kwargs):
            if not hasattr(self, cache_attribute):
                value = method(self, *args, **kwargs)
                if callable(getattr(value, '__iter__', None)) \
                        and not callable(getattr(value, '__len__', None)):
                    value = tuple(value)
                setattr(self, cache_attribute, value)
            return getattr(self, cache_attribute)
        return wrapped


class BuilderBase(object):
    """
    Subclasses of this are for taking some input value (typically an HTML Element, but could be anything), and parsing from it an
    instance of some Record data structure. Instances are single-use: you need to build a new instance for every object that gets
    created. This allows the above metaclass to cache data on `self'.

    2017-02-08 - This is a bit of an experiment, an attempt at making scraper writing a bit more elegant. Maybe experience will
    show that this is overkill and cumbersome, maybe I'll end up using it all the time, we'll see.
    """

    __metaclass__ = BuilderMetaClass

    record_cls = Undef

    def _on_error(self, exception):
        pass

    def __call__(self):
        try:
            kwargs = {}
            for fname,fdef in self.record_cls.record_fields.iteritems():
                value = getattr(self, fname, None)
                if callable(value):
                    value = value()
                kwargs[fname] = value
            return self.record_cls(**kwargs)
        except Exception as ex:
            self._on_error(ex)
            raise

def builder(record_cls):
    return type(
        '%sBuilder' % record_cls.__name__,
        (BuilderBase,),
        {'record_cls': record_cls},
    )

#----------------------------------------------------------------------------------------------------------------------------------

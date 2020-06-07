#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import wraps

#----------------------------------------------------------------------------------------------------------------------------------

class BuilderMetaClass(type):
    """
    If a Builder class for a record class R defines a method called "x_and_y", and "x" and "y" are both fields of R, then new
    methods named "x" and "y" are automatically created, and when either is called, it will call "x_and_y", cache the result (on
    `self'), and return the corresponding value.
    """

    def __new__(mcs, name, bases, attrib):
        return type.__new__(mcs, name, bases, dict(mcs._expand_multiple_field_methods(bases, attrib)))

    @classmethod
    def _expand_multiple_field_methods(mcs, bases, attrib):
        record_cls = mcs._find_record_cls(bases)
        for key, value in attrib.items():
            if record_cls is not None \
                    and '_and_' in key \
                    and callable(value) \
                    and all(f in record_cls.record_fields for f in key.split('_and_')):
                memoized_method = mcs._memoize(key, value)
                for i, f in enumerate(key.split('_and_')):
                    if f in attrib:
                        raise Exception("Can't have both %r and %r" % (key, f))
                    yield f, mcs._single_field_method(memoized_method, i)
            else:
                yield key, value

    @staticmethod
    def _find_record_cls(bases):
        for b in bases:
            record_cls = getattr(b, 'record_cls', None)
            if record_cls:
                return record_cls
        return Exception('record_cls not found')

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

#----------------------------------------------------------------------------------------------------------------------------------

class BuilderBase(object):
    """
    Subclasses of this are for taking some input value (typically an HTML Element, but could be anything), and parsing from it an
    instance of some Record data structure. Instances are single-use: you need to build a new instance for every object that gets
    created. This allows the above metaclass to cache data on `self'.

    2017-02-08 - This is a bit of an experiment, an attempt at making scraper writing a bit more elegant. Maybe experience will
    show that this is overkill and cumbersome, maybe I'll end up using it all the time, we'll see.
    """

    __metaclass__ = BuilderMetaClass

    record_cls = None

    def _on_error(self, exception):
        pass

    def __call__(self):
        try:
            kwargs = {}
            for field_id in self.record_cls.record_fields.keys():
                value = getattr(self, field_id, None)
                if callable(value):
                    value = value()
                kwargs[field_id] = value
            return self.record_cls(**kwargs)  # pylint: disable=not-callable
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

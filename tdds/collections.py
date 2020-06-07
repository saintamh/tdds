#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tdds
from .basics import Field, FieldValueError, compile_field
from .pods import PodsMethodsForSeqTemplate, PodsMethodsForDictTemplate
from .record import FieldHandlingStmtsTemplate
from .unpickler import RecordRegistryMetaClass, RecordUnpickler
from .utils.codegen import SourceCodeTemplate, compile_expr
from .utils.immutabledict import ImmutableDict

#----------------------------------------------------------------------------------------------------------------------------------
# Collection fields are instances of an appropriate subclass of tuple, frozenset, or ImmutableDict. This is the template used to
# generate these subclasses

class CollectionTypeCodeTemplate(SourceCodeTemplate):

    template = '''
        class $class_name($superclass, $RecordRegistryMetaClass(str('Registry'), (object,), {})):

            def $constructor(class_or_self, iter_elems):
                return $superclass.$constructor(class_or_self, $class_name.check_elems(iter_elems))

            $class_fields

            @staticmethod
            def check_elems(iter_elems):
                $check_elems_body

            $pods_methods

            $core_methods

            def __reduce__(self):
                return($RecordUnpickler("$class_name"), ($superclass(self),))
    '''

    RecordRegistryMetaClass = RecordRegistryMetaClass
    RecordUnpickler = RecordUnpickler

    # by default, __repr__, __cmp__ and __hash__ are left to the superclass to implement, but subclasses may override this:
    core_methods = ''

#----------------------------------------------------------------------------------------------------------------------------------
# Subclasses of the above template, one per type

class SequenceCollCodeTemplate(CollectionTypeCodeTemplate):

    superclass = tuple
    constructor = '__new__'
    class_name_suffix = 'Seq'

    def __init__(self, element_field):
        super(SequenceCollCodeTemplate, self).__init__()
        self.class_name = _ucfirst(element_field.type.__name__) + self.class_name_suffix
        self.pods_methods = PodsMethodsForSeqTemplate(element_field)
        self.elem_check_impl = FieldHandlingStmtsTemplate(
            element_field,
            'elem',
            description='[elem]',
        )
        self.class_fields = SourceCodeTemplate(
            'element_field = $element_field',
            element_field=element_field,
        )

    check_elems_body = '''
        for elem in iter_elems:
            $elem_check_impl
            yield elem
    '''

class PairCollCodeTemplate(SequenceCollCodeTemplate):
    FieldValueError = FieldValueError
    class_name_suffix = 'Pair'
    check_elems_body = '''
        num_elems = 0
        for i, elem in enumerate(iter_elems):
            if i > 1:
                raise $FieldValueError("A pair cannot have more than two elements")
            num_elems = i+1
            $elem_check_impl
            yield elem
        if num_elems != 2:
            raise $FieldValueError("A pair must have two elements, not %d" % num_elems)        
    '''

class SetCollCodeTemplate(SequenceCollCodeTemplate):
    superclass = frozenset
    class_name_suffix = 'Set'
    core_methods = '''
        def __cmp__(self, other):
            return cmp(sorted(self), sorted(other))
    '''

class DictCollCodeTemplate(CollectionTypeCodeTemplate):
    superclass = ImmutableDict
    constructor = '__init__'

    def __init__(self, key_field, value_field):
        super(DictCollCodeTemplate, self).__init__()
        self.class_name = '{}To{}Dict'.format(
            _ucfirst(key_field.type.__name__),
            _ucfirst(value_field.type.__name__),
        )
        self.key_handling_stmts = FieldHandlingStmtsTemplate(key_field, 'key', description='<key>')
        self.val_handling_stmts = FieldHandlingStmtsTemplate(value_field, 'value', description='<value>')
        self.pods_methods = PodsMethodsForDictTemplate(key_field, value_field)
        self.class_fields = SourceCodeTemplate(
            '''
            key_field = $key_field
            value_field = $value_field
            ''',
            key_field=key_field,
            value_field=value_field,
        )

    check_elems_body = '''
        for key, value in getattr(iter_elems, "items", iter_elems.__iter__)():
            $key_handling_stmts
            $val_handling_stmts
            yield key, value
    '''

#----------------------------------------------------------------------------------------------------------------------------------

def compile_collection_field(templ, **kwargs):
    verbose = kwargs.pop('__verbose', False)
    collection = compile_expr(templ, templ.class_name, verbose=verbose)
    user_supplied_coerce = kwargs.pop('coerce', None)
    if user_supplied_coerce is None:
        kwargs['coerce'] = lambda elems: collection(elems) if elems is not None else None
    else:
        kwargs['coerce'] = lambda elems: collection(user_supplied_coerce(elems))
    return Field(collection, **kwargs)

# NB there's no reason for the dunder in "__verbose", except that it makes it the same as in the call to `record', where it *is*
# needed.

def seq_of(element_field, **kwargs):
    element_field = compile_field(element_field)
    return compile_collection_field(
        SequenceCollCodeTemplate(element_field),
        subfields=[element_field],
        **kwargs
    )

def pair_of(element_field, **kwargs):
    element_field = compile_field(element_field)
    return compile_collection_field(
        PairCollCodeTemplate(element_field),
        subfields=[element_field],
        **kwargs
    )

def set_of(element_field, **kwargs):
    element_field = compile_field(element_field)
    return compile_collection_field(
        SetCollCodeTemplate(element_field),
        subfields=[element_field],
        **kwargs
    )

def dict_of(key_field, value_field, **kwargs):
    key_field = compile_field(key_field)
    value_field = compile_field(value_field)
    return compile_collection_field(
        DictCollCodeTemplate(key_field, value_field),
        subfields=[key_field, value_field],
        **kwargs
    )

#----------------------------------------------------------------------------------------------------------------------------------
# private utils

def _ucfirst(text):
    return text[0].upper() + text[1:]

#----------------------------------------------------------------------------------------------------------------------------------

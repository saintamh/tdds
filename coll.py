#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id: $
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# saintamh
from ..util.codegen import ClassDefEvaluationNamespace, ExternalValue, SourceCodeTemplate, compile_expr
from ..util.coll import ImmutableDict
from ..util.strings import ucfirst

# this module
from .record import Field, FieldHandlingStmtsTemplate, FieldValueError, Joiner, compile_field_def
from .unpickler import RecordUnpickler, register_class_for_unpickler

#----------------------------------------------------------------------------------------------------------------------------------
# Collection fields are instances of an appropriate subclass of tuple, frozenset, or ImmutableDict. This is the template used to
# generate these subclasses

class CollectionTypeCodeTemplate (SourceCodeTemplate):

    template = '''
        class $cls_name ($superclass):

            def $constructor (cls_or_self, iter_elems):
                return $superclass.$constructor (cls_or_self, $cls_name.check_elems(iter_elems))

            @staticmethod
            def check_elems (iter_elems):
                $pre_loop
                for $elem_ids_loop in $iter_elems:
                    $pre_elem_check
                    $elem_check_impl
                    yield $elem_ids_yield
                $post_loop_check

            def json_struct (self):
                return $json_struct

            # __repr__, __cmp__ and __hash__ are left to the superclass to implement

            def __reduce__ (self):
                return ($RecordUnpickler("$cls_name"), ($superclass(self),))
    '''

    cls_name = NotImplemented
    superclass = NotImplemented
    constructor = '__new__'
    elem_ids_loop = 'elem'
    iter_elems = 'iter_elems'
    elem_ids_yield = 'elem'
    json_struct = 'self'
    pre_elem_check = None
    pre_loop = None
    post_loop_check = None
    elem_check_impl = NotImplemented
    RecordUnpickler = ExternalValue(RecordUnpickler)

#----------------------------------------------------------------------------------------------------------------------------------
# Subclasses of the above template, one per type

class SequenceCollCodeTemplate (CollectionTypeCodeTemplate):
    superclass = 'tuple'
    def __init__ (self, elem_fdef):
        self.cls_name = ucfirst(elem_fdef.type.__name__) + 'Seq'
        self.elem_check_impl = FieldHandlingStmtsTemplate (
            elem_fdef,
            'elem',
            expr_descr='[elem]',
        )

class PairCollCodeTemplate (CollectionTypeCodeTemplate):
    superclass = 'tuple'
    iter_elems = 'enumerate(iter_elems)'
    elem_ids_loop = 'i,elem'
    pre_loop = 'num_elems = 0'
    pre_elem_check = '''
        if i > 1:
            raise $FieldValueError ("A pair cannot have more than two elements")
        num_elems = i+1
    '''
    post_loop_check = '''
        if num_elems != 2:
            raise $FieldValueError ("A pair must have two elements, not %d" % num_elems)
    '''
    FieldValueError = ExternalValue(FieldValueError)
    def __init__ (self, elem_fdef):
        self.cls_name = ucfirst(elem_fdef.type.__name__) + 'Pair'
        self.elem_check_impl = FieldHandlingStmtsTemplate (
            elem_fdef,
            'elem',
            expr_descr='[elem]',
        )

class SetCollCodeTemplate (CollectionTypeCodeTemplate):
    superclass = 'frozenset'
    json_struct = 'tuple(self)'
    def __init__ (self, elem_fdef):
        self.cls_name = ucfirst(elem_fdef.type.__name__) + 'Set'
        self.elem_check_impl = FieldHandlingStmtsTemplate (
            elem_fdef,
            'elem',
            expr_descr='[elem]',
        )

class DictCollCodeTemplate (CollectionTypeCodeTemplate):
    superclass = ExternalValue(ImmutableDict)
    constructor = '__init__'
    elem_ids_loop = 'key,val'
    iter_elems = 'getattr (iter_elems, "iteritems", iter_elems.__iter__)()'
    elem_ids_yield = 'key,val'
    def __init__ (self, key_fdef, val_fdef):
        self.cls_name = '{}To{}Dict'.format (
            ucfirst (key_fdef.type.__name__),
            ucfirst (val_fdef.type.__name__),
        )
        self.elem_check_impl = Joiner ('', values=(
            FieldHandlingStmtsTemplate (key_fdef, 'key', expr_descr='<key>'),
            FieldHandlingStmtsTemplate (val_fdef, 'val', expr_descr='<val>'),
        ))

#----------------------------------------------------------------------------------------------------------------------------------

def make_coll (templ, verbose=False):
    coll_cls = compile_expr (templ, templ.cls_name, verbose=verbose)
    register_class_for_unpickler (templ.cls_name, coll_cls)
    return Field (
        coll_cls,
        coerce = coll_cls,
    )

# NB there's no reason for the dunder in "__verbose", except that it makes it the same as in the call to `record', where it *is*
# needed.

def seq_of (elem_fdef, __verbose=False):
    return make_coll (SequenceCollCodeTemplate(compile_field_def(elem_fdef)), verbose=__verbose)

def pair_of (elem_fdef, __verbose=False):
    return make_coll (PairCollCodeTemplate(compile_field_def(elem_fdef)), verbose=__verbose)

def set_of (elem_fdef, __verbose=False):
    return make_coll (SetCollCodeTemplate(compile_field_def(elem_fdef)), verbose=__verbose)

def dict_of (key_fdef, val_fdef, __verbose=False):
    return make_coll (DictCollCodeTemplate(compile_field_def(key_fdef), compile_field_def(val_fdef)), verbose=__verbose)

#----------------------------------------------------------------------------------------------------------------------------------

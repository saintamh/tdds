#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# saintamh
from ..util.codegen import SourceCodeTemplate, compile_expr
from ..util.coll import ImmutableDict
from ..util.strings import ucfirst

# this module
from .basics import Field, FieldValueError
from .pods import PodsMethodsForSeqTemplate, PodsMethodsForDictTemplate
from .record import FieldHandlingStmtsTemplate
from .unpickler import RecordRegistryMetaClass, RecordUnpickler
from .utils import compile_field_def

#----------------------------------------------------------------------------------------------------------------------------------
# Collection fields are instances of an appropriate subclass of tuple, frozenset, or ImmutableDict. This is the template used to
# generate these subclasses

class CollectionTypeCodeTemplate(SourceCodeTemplate):

    template = '''
        class $cls_name ($superclass):
            __metaclass__ = $RecordRegistryMetaClass

            def $constructor (cls_or_self, iter_elems):
                return $superclass.$constructor (cls_or_self, $cls_name.check_elems(iter_elems))

            $cls_fields

            @staticmethod
            def check_elems (iter_elems):
                $check_elems_body

            $pods_methods

            $core_methods

            def __reduce__ (self):
                return ($RecordUnpickler("$cls_name"), ($superclass(self),))
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
    cls_name_suffix = 'Seq'

    def __init__(self, elem_fdef):
        self.cls_name = ucfirst(elem_fdef.type.__name__) + self.cls_name_suffix
        self.pods_methods = PodsMethodsForSeqTemplate(elem_fdef)
        self.elem_check_impl = FieldHandlingStmtsTemplate(
            elem_fdef,
            'elem',
            expr_descr='[elem]',
        )
        self.cls_fields = SourceCodeTemplate(
            'elem_fdef = $elem_fdef',
            elem_fdef=elem_fdef,
        )

    check_elems_body = '''
        for elem in iter_elems:
            $elem_check_impl
            yield elem
    '''

class PairCollCodeTemplate(SequenceCollCodeTemplate):
    FieldValueError = FieldValueError
    cls_name_suffix = 'Pair'
    check_elems_body = '''
        num_elems = 0
        for i,elem in enumerate(iter_elems):
            if i > 1:
                raise $FieldValueError ("A pair cannot have more than two elements")
            num_elems = i+1
            $elem_check_impl
            yield elem
        if num_elems != 2:
            raise $FieldValueError ("A pair must have two elements, not %d" % num_elems)        
    '''

class SetCollCodeTemplate(SequenceCollCodeTemplate):
    superclass = frozenset
    cls_name_suffix = 'Set'
    core_methods = '''
        def __cmp__ (self, other):
            return cmp(sorted(self), sorted(other))
    '''

class DictCollCodeTemplate(CollectionTypeCodeTemplate):
    superclass = ImmutableDict
    constructor = '__init__'

    def __init__(self, key_fdef, val_fdef):
        self.cls_name = '{}To{}Dict'.format(
            ucfirst(key_fdef.type.__name__),
            ucfirst(val_fdef.type.__name__),
        )
        self.key_handling_stmts = FieldHandlingStmtsTemplate(key_fdef, 'key', expr_descr='<key>')
        self.val_handling_stmts = FieldHandlingStmtsTemplate(val_fdef, 'val', expr_descr='<val>')
        self.pods_methods = PodsMethodsForDictTemplate(key_fdef, val_fdef)
        self.cls_fields = SourceCodeTemplate(
            '''
            key_fdef = $key_fdef
            val_fdef = $val_fdef
            ''',
            key_fdef = key_fdef,
            val_fdef = val_fdef,
        )

    check_elems_body = '''
        for key,val in getattr (iter_elems, "iteritems", iter_elems.__iter__)():
            $key_handling_stmts
            $val_handling_stmts
            yield key,val
    '''

#----------------------------------------------------------------------------------------------------------------------------------

def make_coll(templ, **kwargs):
    verbose = kwargs.pop('__verbose', False)
    coll_cls = compile_expr(templ, templ.cls_name, verbose=verbose)
    user_supplied_coerce = kwargs.pop('coerce', None)
    if user_supplied_coerce is None:
        kwargs['coerce'] = lambda elems: coll_cls(elems) if elems is not None else None
    else:
        kwargs['coerce'] = lambda elems: coll_cls(user_supplied_coerce(elems))
    return Field(coll_cls, **kwargs)

# NB there's no reason for the dunder in "__verbose", except that it makes it the same as in the call to `record', where it *is*
# needed.

def seq_of(elem_fdef, **kwargs):
    elem_fdef = compile_field_def(elem_fdef)
    return make_coll(
        SequenceCollCodeTemplate(elem_fdef),
        subfields = [elem_fdef],
        **kwargs
    )

def pair_of(elem_fdef, **kwargs):
    elem_fdef = compile_field_def(elem_fdef)
    return make_coll(
        PairCollCodeTemplate(elem_fdef),
        subfields = [elem_fdef],
        **kwargs
    )

def set_of(elem_fdef, **kwargs):
    elem_fdef = compile_field_def(elem_fdef)
    return make_coll(
        SetCollCodeTemplate(elem_fdef),
        subfields = [elem_fdef],
        **kwargs
    )

def dict_of(key_fdef, val_fdef, **kwargs):
    key_fdef = compile_field_def(key_fdef)
    val_fdef = compile_field_def(val_fdef)
    return make_coll(
        DictCollCodeTemplate(key_fdef, val_fdef),
        subfields = [key_fdef, val_fdef],
        **kwargs
    )

#----------------------------------------------------------------------------------------------------------------------------------
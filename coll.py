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
from ..util.codegen import ClassDefEvaluationNamespace, SourceCodeTemplate, compile_expr

# this module
from .record import FieldHandlingStmtsTemplate, compile_field_def

#----------------------------------------------------------------------------------------------------------------------------------
# collection fields (seq_of, dict_of, pair_of, set_of)

class CollectionTypeCodeTemplate (SourceCodeTemplate):

    template = '''
        class $cls_name ($superclass):

            def __init__ (self, iter_elems):
                super(self.__class__,self).__init__ (self.check_elems(iter_elems))
                $post_init_check

            @classmethod
            def check_elems (cls, iter_elems):
                for $elem_ids_loop in $iter_elems:
                    $pre_check
                    $elem_check_impl
                    yield $elem_ids_yield

            def json_struct (self):
                return $json_struct
    '''

    iter_elems = 'iter_elems'
    post_init_check = None
    json_struct = 'self'
    pre_check = None
    elem_check_impl = NotImplemented

    def __init__ (self, cls_name, superclass):
        super(CollectionTypeCodeTemplate,self).__init__()
        self.cls_name = cls_name
        self.superclass = superclass

#----------------------------------------------------------------------------------------------------------------------------------
# seq_of

class SequenceCollCodeTemplate (CollectionTypeCodeTemplate):
    elem_ids_loop = 'elem'
    elem_ids_yield = 'elem'
    def __init__ (self, elem_fdef):
        super(SequenceCollCodeTemplate,self).__init__ (ucfirst(elem_fdef.type.__name__)+'Seq', 'tuple')
        self.elem_fdef = elem_fdef
    @property
    def elem_check_impl (self):
        return FieldHandlingStmtsTemplate (self.elem_fdef, 'elem', expr_descr='<elem>')

def seq_of (fdef, verbose=False):
    templ = SequenceCollCodeTemplate (compile_field_def(fdef))
    return compile_expr (templ, templ.cls_name, verbose=verbose)

#----------------------------------------------------------------------------------------------------------------------------------
# pair_or

class PairCollCodeTemplate (CollectionTypeCodeTemplate):

    iter_elems = 'enumerate(iter_elems)'
    elem_ids_loop = 'i,elem'
    elem_ids_yield = 'elem'
    pre_check = '''
        if i > 1:
            raise ValueError ("A pair can only have two elements")
    '''

    def __init__ (self, elem_fdef):
        super(PairCollCodeTemplate,self).__init__ ('Pair', 'tuple')
        self.elem_fdef = elem_fdef

    @property
    def elem_check_impl (self):
        return FieldHandlingStmtsTemplate (self.elem_fdef, 'elem', expr_descr='<elem>')

def pair_of (fdef):
    coll_gen = PairCollCodeTemplate (compile_field_def(fdef))
    print coll_gen.expand (ClassDefEvaluationNamespace())

#----------------------------------------------------------------------------------------------------------------------------------

def set_of (elem_type):
    "TODO"

#----------------------------------------------------------------------------------------------------------------------------------

class ImmutableDict (dict):
    def forbidden_operation (self, *args, **kwargs):
        raise TypeError ("ImmutableDict instances are read-only")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = forbidden_operation
    def __hash__ (self, _cache=[]):
        if not _cache:
            h = 0
            for key,val in sorted(self.iteritems()):
                h = (h*2209 + hash(key)*47 + hash(val)) % 15485863
            _cache.append (h)
        return _cache[0]
    # We just defer to the built-in __cmp__ for dicts

def dict_of (key_type, val_type, **kwargs):
    "TODO"

#----------------------------------------------------------------------------------------------------------------------------------
# misc utils

def ucfirst (s):
    # like s.capitalize(), but only affects the 1st letter, leaves the rest untouched
    return s[:1].upper() + s[1:]

#----------------------------------------------------------------------------------------------------------------------------------

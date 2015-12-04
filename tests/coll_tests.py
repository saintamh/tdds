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
from ...util.coll import ImmutableDict

# this module
from .. import *
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# seq_of

@test("seq_of fields can be defined using a tuple")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=(1,2,3))
    assert_eq (r.elems, (1,2,3))

@test("seq_of fields can be defined using a list")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=[1,2,3])
    assert_eq (r.elems, (1,2,3))

@test("seq_of fields can be defined using an iterator")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=(i for i in [1,2,3]))
    assert_eq (r.elems, (1,2,3))

@test("seq_of fields can be defined using any iterable")
def _():
    class MyIterable (object):
        def __iter__ (self):
            for i in (1,2,3):
                yield i
    R = record ('R', elems=seq_of(int))
    r = R(elems=MyIterable())
    assert_eq (r.elems, (1,2,3))

@test("seq_of fields are tuples, and therefore immutable")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=[1,2,3])
    with expected_error(TypeError):
        r.elems[2] = 4

@test("elements of the sequence must be of the correct type")
def _():
    R = record ('R', elems=seq_of(int))
    with expected_error(FieldTypeError):
        R(elems=['1','2','3'])

@test("Two sequences can use types of the same name, they won't clash")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=seq_of(C1))
    R2 = record ('R2', elems=seq_of(C2))
    r1 = R1(elems=[C1()])
    r2 = R2(elems=[C2()])
    assert_eq (r1.elems.__class__.__name__, 'ElementSeq')
    assert_eq (r2.elems.__class__.__name__, 'ElementSeq')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sequences use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=seq_of(C1))
    R2 = record ('R2', elems=seq_of(C2))
    with expected_error(FieldTypeError):
        R1 (elems=[C2()])

@test("seq_of params can be field defs themselves")
def _():
    R = record (
        'R',
        elems = seq_of(pair_of(int)),
    )
    with expected_error (FieldValueError):
        R ([(1,2,3)])
    assert_eq (
        R([(1,2),(3,4)]).elems,
        ((1,2),(3,4)),
    )

@test("a nullable seq can be null")
def _():
    R = record ('R', v=nullable(seq_of(int)))
    s = R(None)
    assert_is (s.v, None)

#----------------------------------------------------------------------------------------------------------------------------------
# pair_of

@test("pair_of fields can be defined using any iterable")
def _():
    class MyIterable (object):
        def __iter__ (self):
            yield 1
            yield 2
    R = record ('R', elems=pair_of(int))
    r = R(elems=MyIterable())
    assert_eq (r.elems, (1,2))

@test("pair_of fields are tuples, and therefore immutable")
def _():
    R = record ('R', elems=pair_of(int))
    r = R(elems=[1,2])
    with expected_error(TypeError):
        r.elems[1] = 4
    assert_eq (r.elems, (1,2))

@test("elements of the pair must be of the correct type")
def _():
    R = record ('R', elems=pair_of(int))
    with expected_error(FieldTypeError):
        R(elems=['1','2'])

@test("pairs cannot have 1 element")
def _():
    R = record ('R', elems=pair_of(int))
    with expected_error(FieldValueError):
        R(elems=[1])

@test("pairs cannot have more than 2")
def _():
    R = record ('R', elems=pair_of(int))
    with expected_error(FieldValueError):
        R(elems=[1,2,3
        ])

@test("Two pairs can use types of the same name, they won't clash")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=pair_of(C1))
    R2 = record ('R2', elems=pair_of(C2))
    r1 = R1(elems=[C1(),C1()])
    r2 = R2(elems=[C2(),C2()])
    assert_eq (r1.elems.__class__.__name__, 'ElementPair')
    assert_eq (r2.elems.__class__.__name__, 'ElementPair')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two pairs use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=pair_of(C1))
    R2 = record ('R2', elems=pair_of(C2))
    with expected_error(FieldTypeError):
        R1 (elems=[C2(),C2()])

@test("a nullable pair can be null")
def _():
    R = record ('R', v=nullable(pair_of(int)))
    s = R(None)
    assert_is (s.v, None)

#----------------------------------------------------------------------------------------------------------------------------------
# set_of

@test("set_of fields can be defined using any iterable")
def _():
    class MyIterable (object):
        def __iter__ (self):
            for i in (1,2,3):
                yield i
    R = record ('R', elems=set_of(int))
    r = R(elems=MyIterable())
    assert_eq (r.elems, frozenset([1,2,3]))

@test("set_of fields are frozenset instances, and therefore immutable")
def _():
    R = record ('R', elems=set_of(int))
    r = R(elems=[1,2,3])
    isinstance (r.elems, frozenset)

@test("elements of the set must be of the correct type")
def _():
    R = record ('R', elems=set_of(int))
    with expected_error(FieldTypeError):
        R(elems=['1','2','3'])

@test("Two sets can use types of the same name, they won't clash")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=set_of(C1))
    R2 = record ('R2', elems=set_of(C2))
    r1 = R1(elems=[C1()])
    r2 = R2(elems=[C2()])
    assert_eq (r1.elems.__class__.__name__, 'ElementSet')
    assert_eq (r2.elems.__class__.__name__, 'ElementSet')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sets use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=set_of(C1))
    R2 = record ('R2', elems=set_of(C2))
    with expected_error(FieldTypeError):
        R1 (elems=[C2()])

@test("a nullable set can be null")
def _():
    R = record ('R', v=nullable(set_of(int)))
    s = R(None)
    assert_is (s.v, None)

#----------------------------------------------------------------------------------------------------------------------------------
# dict_of

@test("dict_of fields can be defined using a dict")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems={1:'uno',2:'zwei'})
    assert_eq (r.elems, {1:'uno',2:'zwei'})

@test("dict_of fields can be defined using an iterator of key/value pairs")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems=(iter([[1,'uno'],[2,'zwei']])))
    assert_eq (r.elems, {1:'uno',2:'zwei'})

@test("keys of the dict must be of the correct type")
def _():
    R = record ('R', elems=dict_of(int,str))
    with expected_error(FieldTypeError):
        R(elems={'1':'uno'})

@test("values of the dict must be of the correct type")
def _():
    R = record ('R', elems=dict_of(int,str))
    with expected_error(FieldTypeError):
        R(elems={1:1})

@test("dict_of fields are ImmutableDict instances, and therefore immutable")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems={1:'uno',2:'zwei'})
    assert isinstance (r.elems, ImmutableDict)

@test("Two dicts can use types of the same name, they won't clash")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=dict_of(int,C1))
    R2 = record ('R2', elems=dict_of(int,C2))
    r1 = R1(elems={9:C1()})
    r2 = R2(elems={9:C2()})
    assert_eq (r1.elems.__class__.__name__, 'IntToElementDict')
    assert_eq (r2.elems.__class__.__name__, 'IntToElementDict')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sets use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=dict_of(int,C1))
    R2 = record ('R2', elems=dict_of(int,C2))
    with expected_error(FieldTypeError):
        R1 (elems={9:C2()})

@test("dict_of params can be field defs themselves")
def _():
    R = record (
        'R',
        elems = dict_of (
            str,
            pair_of (int),
        ),
    )
    with expected_error (FieldTypeError):
        R ({object(): (1,2)})
    with expected_error (FieldValueError):
        R ({'ABC': (1,2,3)})
    assert_eq (
        R({'ABC':(1,2)}).elems,
        {'ABC': (1,2)},
    )

@test("a nullable dict can be null")
def _():
    R = record ('R', v=nullable(dict_of(int,int)))
    s = R(None)
    assert_is (s.v, None)

#----------------------------------------------------------------------------------------------------------------------------------
# ImmutableDict

@test("ImmutableDict objects are immutable, and therefore you can't assign to their keys")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems[2] = 'two'
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't delete their keys")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        del elems[2]
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .clear() on them")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems.clear()
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .pop() on them")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems.pop(1)
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .popitem() on them")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems.popitem()
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .setdefault() on them")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems.setdefault(3,'trois')
    assert_eq (elems, {1:'uno',2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .update() on them")
def _():
    elems = ImmutableDict ({1:'uno',2:'zwei'})
    with expected_error(TypeError):
        elems.update({3:'trois'})
    assert_eq (elems, {1:'uno',2:'zwei'})

#----------------------------------------------------------------------------------------------------------------------------------

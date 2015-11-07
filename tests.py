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
from collections import Counter
from functools import wraps

# this module
from .record import \
    Field, ImmutableDict, \
    FieldCheckFailed, FieldIsNotNullable, RecordsAreImmutable, \
    record, \
    dict_of, pair_of, seq_of, set_of, \
    one_of, \
    nonnegative, nullable, strictly_positive, \
    uppercase_letters, uppercase_wchars, uppercase_hex, lowercase_letters, lowercase_wchars, lowercase_hex, digits_str, \
    absolute_http_url

#----------------------------------------------------------------------------------------------------------------------------------
# TODO

# non-nullable collections cannot be empty

# types ref'ed by name (e.g. for a LinkedList's "next")

# datetime, timedelta objects

# const

#----------------------------------------------------------------------------------------------------------------------------------
# plumbing

ALL_TESTS = []

class TestFailure (Exception):
    pass

def test (test_id):
    def register_test_func (func):
        ALL_TESTS.append ((test_id, func))
        return func
    return register_test_func

class expected_error (object):
    def __init__ (self, exc_type):
        self.exc_type = exc_type
    def __enter__ (self):
        pass
    def __exit__ (self, exc_type, exc_value, exc_tb):
        if exc_type is self.exc_type:
            return True # swallow the exception, test passes
        elif exc_type is None:
            raise TestFailure ("Expected %s, no exception raised" % self.exc_type.__name__)
        else:
            raise TestFailure ("Raised %s instead of %s" % (exc_type.__name__, self.exc_type.__name__))

def assert_eq (v1, v2):
    if v1 != v2:
        raise AssertionError ("%r != %r" % (v1,v2))

#----------------------------------------------------------------------------------------------------------------------------------

@test('records are immutable')
def _():
    R = record ('R', id = int)
    r = R(10)
    with expected_error(RecordsAreImmutable):
        r.id = 11

#----------------------------------------------------------------------------------------------------------------------------------
# scalar fields

SCALAR_TYPES = (int,long,float,str,unicode)

def val_type_tests (val_type):
    val_type_name = val_type.__name__

    @test("non-nullable {} fields can't be None".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        with expected_error(FieldIsNotNullable):
            R(id=None)

    @test("non-nullable {} fields can be zero".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        v = val_type(0)
        r = R(id=v)
        assert_eq (r.id, v)

    @test("nullable {} fields can be None".format(val_type_name))
    def _():
        R = record ('R', id=nullable(val_type))
        r = R(id=None)
        assert r.id is None, repr(r.id)

    @test("{} fields can be defined with just the type".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        r = R(id=val_type(1))

    @test("{} fields defined with just the type are not nullable".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        with expected_error(FieldIsNotNullable):
            R(id=None)

for val_type in SCALAR_TYPES:
    # they need to be within their own scope for the `val_type' to be properly set
    val_type_tests (val_type)

#----------------------------------------------------------------------------------------------------------------------------------
# more type checks

@test("objects can be of a subclass of the declared type")
def _():
    class Parent (object):
        pass
    class Child (Parent):
        pass
    R = record ('R', obj=Parent)
    c = Child()
    r = R(c)
    assert r.obj is c

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
    with expected_error(TypeError):
        R(elems=['1','2','3'])

@test("Two sequences can use types of the same name, they won't clash")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=seq_of(C1))
    R2 = record ('R2', elems=seq_of(C2))
    r1 = R1(elems=[C1()])
    r2 = R2(elems=[C2()])
    assert_eq (r1.elems.__class__.__name__, 'ElementSequence')
    assert_eq (r2.elems.__class__.__name__, 'ElementSequence')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sequences use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=seq_of(C1))
    R2 = record ('R2', elems=seq_of(C2))
    with expected_error(TypeError):
        R1 (elems=[C2()])

@test("sequence fields get serialized for JSON as tuples")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=[1,2,3])
    assert_eq (r.json_struct(), {
        "elems": (1,2,3),
    })

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
    with expected_error(TypeError):
        R(elems=['1','2'])

@test("pairs cannot have 1 element")
def _():
    R = record ('R', elems=pair_of(int))
    with expected_error(ValueError):
        R(elems=[1])

@test("pairs cannot have more than 2")
def _():
    R = record ('R', elems=pair_of(int))
    with expected_error(ValueError):
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
    with expected_error(TypeError):
        R1 (elems=[C2(),C2()])

@test("pair fields get serialized for JSON as tuples")
def _():
    R = record ('R', elems=pair_of(int))
    r = R(elems=[1,2])
    assert_eq (r.json_struct(), {
        "elems": (1,2),
    })

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
    with expected_error(TypeError):
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
    with expected_error(TypeError):
        R1 (elems=[C2()])

@test("pair fields get serialized for JSON as tuples")
def _():
    R = record ('R', elems=set_of(int))
    r = R(elems=[1,2,2,3])
    json_elems = r.json_struct()['elems']
    assert isinstance (json_elems, tuple), repr(json_elems)
    assert_eq (
        sorted(json_elems),
        [1,2,3],
    )

#----------------------------------------------------------------------------------------------------------------------------------
# dict_of

@test("dict_of fields can be defined using a dict")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems={1:'uno',2:'zwei'})
    assert_eq (r.elems, {1:'uno',2:'zwei'})

@test("dict_of fields can be defined using an iterator")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems=((k,v) for k,v in [[1,'uno'],[2,'zwei']]))
    assert_eq (r.elems, {1:'uno',2:'zwei'})

@test("keys of the dict must be of the correct type")
def _():
    R = record ('R', elems=dict_of(int,str))
    with expected_error(TypeError):
        R(elems={'1':'uno'})

@test("values of the dict must be of the correct type")
def _():
    R = record ('R', elems=dict_of(int,str))
    with expected_error(TypeError):
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
    assert_eq (r1.elems.__class__.__name__, 'IntElementDictionary')
    assert_eq (r2.elems.__class__.__name__, 'IntElementDictionary')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sets use types of the same name, you still can't put one's elems in the other")
def _():
    C1 = type ('Element', (object,), {})
    C2 = type ('Element', (object,), {})
    R1 = record ('R1', elems=dict_of(int,C1))
    R2 = record ('R2', elems=dict_of(int,C2))
    with expected_error(TypeError):
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
    with expected_error (FieldCheckFailed):
        R ({'ABCD': (1,2)})
    with expected_error (FieldCheckFailed):
        R ({'ABC': (1,2,3)})
    assert_eq (
        R({'ABC':(1,2)}).elems,
        {'ABC': (1,2)},
    )

@test("dict_of fields get serialized for JSON as dicts")
def _():
    R = record ('R', elems=dict_of(int,str))
    r = R(elems={1:'uno',2:'zwei'})
    assert_eq (r.json_struct(), {
        "elems": {1:'uno',2:'zwei'},
    })

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
# JSON serialization

@test("scalar fields are directly rendered to JSON")
def _():
    R = record ('R', id=str, label=unicode)
    r = R (id='robert', label=u"Robert Smith")
    j = r.json_struct()
    assert_eq (j, {
        "id": "robert",
        "label": "Robert Smith",
    })

@test("nested records are rendered to JSON as nested objects")
def _():
    Name = record ('Name', first=unicode, last=unicode)
    Person = record ('Person', name=Name, age=int)
    p = Person (name=Name(first=u"Robert",last=u"Smith"), age=100)
    j = p.json_struct()
    assert_eq (j, {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    })

@test("the nested object can be anything with a json_struct() method")
def _():
    class Name (object):
        def __init__ (self, first, last):
            self.first = first
            self.last = last
        def json_struct (self):
            return {'first':self.first, 'last':self.last}
    Person = record ('Person', name=Name, age=int)
    p = Person (name=Name(first=u"Robert",last=u"Smith"), age=100)
    j = p.json_struct()
    assert_eq (j, {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    })

#----------------------------------------------------------------------------------------------------------------------------------
# "coerce" functions

@test("a 'coerce' function specified as a lambda can modify the value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: s.upper(),
    ))
    r = R('a')
    assert_eq (r.id, 'A')

@test("a 'coerce' function specified as any callable can modify the value")
def _():
    class Upper (object):
        def __call__ (self, s):
            return s.upper()
    R = record ('R', id=Field (
        type = str,
        coerce = Upper(),
    ))
    r = R('a')
    assert_eq (r.id, 'A')

@test("a 'coerce' function specified as a string can modify the value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = '{}.upper()',
    ))
    r = R('a')
    assert_eq (r.id, 'A')

@test("the 'coerce' function is invoked before the null check and therefore may get a None value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = str,
    ))
    r = R(None)
    assert_eq (r.id, 'None')

@test("the 'coerce' function may not return None if the field is not nullable")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: None,
    ))
    with expected_error(FieldIsNotNullable):
        r = R('a')

@test("the 'coerce' function may return None if the field is nullable")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: None,
        nullable = True,
    ))
    r = R('a')
    assert r.id is None, repr(r.id)

@test("specifying something other than a string or a callable as 'coerce' raises a TypeError")
def _():
    with expected_error(TypeError):
        R = record ('R', id=Field (
            type = str,
            coerce = 0,
        ))

@test("the coercion function must return a value of the correct type")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda v: 10,
    ))
    with expected_error(TypeError):
        R(id='not ten')

@test("is the field is not nullable, the coercion function may not return None")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda v: None,
    ))
    with expected_error(FieldIsNotNullable):
        R(id='not None')

@test("is the field is nullable, the coercion function is run on the default value")
def _():
    R = record ('R', id=Field (
        type = str,
        nullable = True,
        default = 'lower',
        coerce = lambda v: v.upper(),
    ))
    r = R(id=None)
    assert_eq (r.id, 'LOWER')

#----------------------------------------------------------------------------------------------------------------------------------
# 'check' function

@test("if the 'check' function returns False, a FieldCheckFailed exception is raised")
def _():
    R = record ('R', id=Field (
        type = str,
        check = lambda s: s == 'valid',
    ))
    with expected_error(FieldCheckFailed):
        r = R('invalid')

@test("if the 'check' function returns True, no FieldCheckFailed exception is raised")
def _():
    R = record ('R', id=Field (
        type = str,
        check = lambda s: s == 'valid',
    ))
    r = R('valid')

@test("a 'check' function specified as any callable can validate the value")
def _():
    class Upper (object):
        def __call__ (self, s):
            return s == 'valid'
    R = record ('R', id=Field (
        type = str,
        check = Upper(),
    ))
    r = R('valid')

@test("a 'check' function specified as a string can validate the value")
def _():
    R = record ('R', id=Field (
        type = str,
        check = '{} == "valid"',
    ))
    r = R('valid')

@test("the 'check' function is invoked after the null check and will not receive a None value if the field is not nullable")
def _():
    def not_none (value):
        if value is None:
            raise BufferError()
    R = record ('R', id=Field (
        type = str,
        coerce = not_none,
    ))
    with expected_error(BufferError):
        r = R(None)

@test("the 'check' function may raise exceptions, these are not caught and bubble up")
def _():
    def boom (value):
        raise BufferError ('boom')
    R = record ('R', id=Field (
        type = str,
        check = boom,
    ))
    with expected_error(BufferError):
        r = R('a')

@test("specifying something other than a string or a callable as 'check' raises a TypeError")
def _():
    with expected_error(TypeError):
        R = record ('R', id=Field (
            type = str,
            check = 0,
        ))

@test("if both a default value and a check are provided, the check is invoked on the default value, too")
def _():
    R = record ('R', id=Field (
        type = str,
        nullable = True,
        default = 'abra',
        check = lambda s: value == 'cadabra',
    ))

@test("the coercion function runs before the check, and may change a bad value to a good one")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: s.upper(),
        check = lambda s: s == s.upper(),
    ))
    r2 = R('ok')
    assert_eq (r2.id, 'OK')

@test("the output of the coercion function is passed to the check function, which may reject it")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: s.lower(),
        check = lambda s: s == s.upper(),
    ))
    with expected_error(FieldCheckFailed):
        r2 = R('OK')

#----------------------------------------------------------------------------------------------------------------------------------
# pickleablity

for protocol in (0,1,2,-1):

    @test("records can be pickled and unpickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        R = record ('R', id=int, label=unicode)
        r1 = R (id=1, label=u"uno")
        r2 = pickle.loads (pickle.dumps (r1, protocol=protocol))
        assert_eq (r2, r1)

#----------------------------------------------------------------------------------------------------------------------------------
# number utils

@test("nonnegative numbers cannot be smaller than zero")
def _():
    R = record ('R', id=nonnegative(int))
    with expected_error(FieldCheckFailed):
        R(id=-1)

@test("nonnegative numbers can be zero")
def _():
    R = record ('R', id=nonnegative(int))
    assert_eq (R(id=0).id, 0)

@test("nonnegative numbers can be greater than zero")
def _():
    R = record ('R', id=nonnegative(int))
    assert_eq (R(id=10).id, 10)

@test("strictly_positive numbers cannot be smaller than zero")
def _():
    R = record ('R', id=strictly_positive(int))
    with expected_error(FieldCheckFailed):
        R(id=-1)

@test("strictly_positive numbers cannot be zero")
def _():
    R = record ('R', id=strictly_positive(int))
    with expected_error(FieldCheckFailed):
        R(id=0)

@test("strictly_positive numbers can be greater than zero")
def _():
    R = record ('R', id=strictly_positive(int))
    assert_eq (R(id=10).id, 10)

#----------------------------------------------------------------------------------------------------------------------------------
# string utils

@test("uppercase_letters(3) accepts 3 uppercase letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    assert_eq (R(s='ABC').s, 'ABC')

@test("uppercase_letters(3) doesn't accept less than 3 letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldCheckFailed):
        R(s='AB')

@test("uppercase_letters(3) doesn't accept more than 3 letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldCheckFailed):
        R(s='ABCD')

@test("uppercase_letters doesn't accept lowercase letters")
def _():
    R = record ('R', s=uppercase_letters(3))
    with expected_error(FieldCheckFailed):
        R(s='abc')

@test("uppercase_letters() accepts any number of uppercase letters")
def _():
    R = record ('R', s=uppercase_letters())
    assert_eq (R(s='ABCDEFGH').s, 'ABCDEFGH')

@test("uppercase_letters() accepts empty strings")
def _():
    R = record ('R', s=uppercase_letters())
    assert_eq (R(s='').s, '')

@test("uppercase_letters() still only accepts uppercase letters")
def _():
    R = record ('R', s=uppercase_letters())
    with expected_error(FieldCheckFailed):
        R(s='a')

#----------------------------------------------------------------------------------------------------------------------------------
# one_of

@test("one_of accepts a fixed list of values")
def _():
    R = record ('R', v=one_of('a','b','c'))
    assert_eq (R(v='a').v, 'a')

@test("one_of doesn't accept values outside the given list")
def _():
    R = record ('R', v=one_of('a','b','c'))
    with expected_error(FieldCheckFailed):
        R(v='d')

@test("one_of does not accept an empty argument list")
def _():
    with expected_error(ValueError):
        one_of()

@test("all arguments to one_of must have the same type")
def _():
    with expected_error(ValueError):
        one_of ('a',object())
    
@test("one_of compares values based on == rather than `is'")
def _():
    class C (object):
        def __init__ (self, value):
            self.value = value
        def __cmp__ (self, other):
            return cmp (self.value[0], other.value[0])
        def __hash__ (self):
            return hash(self.value[0])
    c1 = C (['a','bcde'])
    c2 = C (['a','bracadabra'])
    R = record ('R', c=one_of(c1))
    assert_eq (R(c=c2).c, c2)

#----------------------------------------------------------------------------------------------------------------------------------

def main ():
    tally = Counter()
    test_id_fmt = "{{:.<{width}}}".format (width = 3 + max (len(test_id) for test_id,test_func in ALL_TESTS))
    result_fmt = "[{:^4}] {}"
    for test_id,test_func in ALL_TESTS:
        tally['total'] += 1
        print test_id_fmt.format(test_id+' '),
        try:
            test_func()
        except Exception, ex:
            print result_fmt.format ('FAIL', '{}: {}'.format(ex.__class__.__name__, ex))
            tally['failed'] += 1
        else:
            print result_fmt.format ('OK', '')
            tally['passed'] += 1
    print
    for item in sorted (tally.items()):
        print "{}: {}".format(*item)

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------

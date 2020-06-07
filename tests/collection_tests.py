#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tdds
from tdds import (
    Field,
    FieldNotNullable,
    FieldTypeError,
    FieldValueError,
    ImmutableDict,
    Record,
    dict_of,
    nullable,
    pair_of,
    seq_of,
    set_of,
)
from tdds.utils.compatibility import native_string, text_type

# this module
from .plumbing import assert_eq, assert_is, assert_none, assert_raises, build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# seq_of

@test('seq_of fields can be defined using a tuple')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=(1, 2, 3))
    assert_eq(r.elems, (1, 2, 3))

@test('seq_of fields can be defined using a list')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=[1, 2, 3])
    assert_eq(r.elems, (1, 2, 3))

@test('seq_of fields can be defined using an iterator')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=(i for i in [1, 2, 3]))
    assert_eq(r.elems, (1, 2, 3))

@test('seq_of fields can be defined using any iterable')
def _():
    class MyIterable(object):
        def __iter__(self):
            for i in (1, 2, 3):
                yield i
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=MyIterable())
    assert_eq(r.elems, (1, 2, 3))

@test('seq_of fields are tuples, and therefore immutable')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    r = MyRecord(elems=[1, 2, 3])
    with assert_raises(TypeError):
        r.elems[2] = 4  # pylint: disable=unsupported-assignment-operation

@test('elements of the sequence must be of the correct type')
def _():
    class MyRecord(Record):
        elems = seq_of(int)
    with assert_raises(FieldTypeError):
        MyRecord(elems=['1', '2', '3'])

@test("Two sequences can use types of the same name, they won't clash")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class Record1(Record):
        elems = seq_of(MyClass1)
    class Record2(Record):
        elems = seq_of(MyClass2)
    r1 = Record1(elems=[MyClass1()])
    r2 = Record2(elems=[MyClass2()])
    assert_eq(r1.elems.__class__.__name__, 'ElementSeq')
    assert_eq(r2.elems.__class__.__name__, 'ElementSeq')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sequences use types of the same name, you still can't put one's elems in the other")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class MyRecord(Record):
        elems = seq_of(MyClass1)
    with assert_raises(FieldTypeError):
        MyRecord(elems=[MyClass2()])

@test('seq_of params can be field defs themselves')
def _():
    class MyRecord(Record):
        elems = seq_of(pair_of(int))
    with assert_raises(FieldValueError):
        MyRecord([(1, 2, 3)])
    assert_eq(
        MyRecord([(1, 2), (3, 4)]).elems,
        ((1, 2), (3, 4)),
    )

@test('a nullable seq can be null')
def _():
    class MyRecord(Record):
        v = nullable(seq_of(int))
    s = MyRecord(None)
    assert_is(s.v, None)

@test('seq_of types can be defined using the Field class')
def _():
    class MyRecord(Record):
        v = seq_of(Field(int))
    assert_eq(MyRecord((1, 2, 3)).v, (1, 2, 3))

@test("seq_of accepts a `coerce' kwarg")
def _():
    class MyRecord(Record):
        v = seq_of(
            int,
            coerce=lambda v: map(int, v),
        )
    assert_eq(
        MyRecord('123').v,
        (1, 2, 3),
    )

@test("seq_of accepts a `check' kwarg")
def _():
    class MyRecord(Record):
        v = seq_of(
            int,
            check=lambda s: len(s) == 3,
        )
    assert_eq(MyRecord((1, 2, 3)).v, (1, 2, 3))
    with assert_raises(FieldValueError):
        MyRecord((1, 2, 3, 4))

@test("seq_of accepts a `nullable' kwarg")
def _():
    class MyRecord1(Record):
        v = seq_of(int, nullable=True)
    assert_none(MyRecord1().v)
    assert_none(MyRecord1(None).v)
    class MyRecord2(Record):
        v = seq_of(int, nullable=False)
    with assert_raises(TypeError):
        MyRecord2()
    with assert_raises(FieldNotNullable):
        MyRecord2(None)

@test("seq_of accepts a `default' kwarg")
def _():
    class MyRecord(Record):
        v = seq_of(
            int,
            nullable=True,
            default=(1, 2, 3),
        )
    assert_eq(MyRecord((4, 5, 6)).v, (4, 5, 6))
    assert_eq(MyRecord(None).v, (1, 2, 3))
    assert_eq(MyRecord().v, (1, 2, 3))

#----------------------------------------------------------------------------------------------------------------------------------
# pair_of

@test('pair_of fields can be defined using any iterable')
def _():
    class MyIterable(object):
        def __iter__(self):
            yield 1
            yield 2
    class MyRecord(Record):
        elems = pair_of(int)
    r = MyRecord(elems=MyIterable())
    assert_eq(r.elems, (1, 2))

@test('pair_of fields are tuples, and therefore immutable')
def _():
    class MyRecord(Record):
        elems = pair_of(int)
    r = MyRecord(elems=[1, 2])
    with assert_raises(TypeError):
        r.elems[1] = 4  # pylint: disable=unsupported-assignment-operation
    assert_eq(r.elems, (1, 2))

@test('elements of the pair must be of the correct type')
def _():
    class MyRecord(Record):
        elems = pair_of(int)
    with assert_raises(FieldTypeError):
        MyRecord(elems=['1', '2'])

@test('pairs cannot have 1 element')
def _():
    class MyRecord(Record):
        elems = pair_of(int)
    with assert_raises(FieldValueError):
        MyRecord(elems=[1])

@test('pairs cannot have more than 2')
def _():
    class MyRecord(Record):
        elems = pair_of(int)
    with assert_raises(FieldValueError):
        MyRecord(elems=[1, 2, 3])

@test("Two pairs can use types of the same name, they won't clash")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class Record1(Record):
        elems = pair_of(MyClass1)
    class Record2(Record):
        elems = pair_of(MyClass2)
    r1 = Record1(elems=[MyClass1(), MyClass1()])
    r2 = Record2(elems=[MyClass2(), MyClass2()])
    assert_eq(r1.elems.__class__.__name__, 'ElementPair')
    assert_eq(r2.elems.__class__.__name__, 'ElementPair')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two pairs use types of the same name, you still can't put one's elems in the other")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class MyRecord(Record):
        elems = pair_of(MyClass1)
    with assert_raises(FieldTypeError):
        MyRecord(elems=[MyClass2(), MyClass2()])

@test('a nullable pair can be null')
def _():
    class MyRecord(Record):
        v = nullable(pair_of(int))
    s = MyRecord(None)
    assert_is(s.v, None)

@test('pair_of types can be defined using the Field class')
def _():
    class MyRecord(Record):
        v = pair_of(Field(int))
    assert_eq(MyRecord((1, 2)).v, (1, 2))

@test("pair_of accepts a `coerce' kwarg")
def _():
    class MyRecord(Record):
        v = pair_of(
            int,
            coerce=lambda v: map(int, v),
        )
    assert_eq(
        MyRecord('12').v,
        (1, 2),
    )

@test("pair_of accepts a `check' kwarg")
def _():
    class MyRecord(Record):
        v = pair_of(
            int,
            check=lambda s: sum(s) == 3,
        )
    assert_eq(MyRecord((1, 2)).v, (1, 2))
    with assert_raises(FieldValueError):
        MyRecord((4, 5))

@test("pair_of accepts a `nullable' kwarg")
def _():
    class MyRecord1(Record):
        v = pair_of(int, nullable=True)
    assert_none(MyRecord1().v)
    assert_none(MyRecord1(None).v)
    class MyRecord2(Record):
        v = pair_of(int, nullable=False)
    with assert_raises(TypeError):
        MyRecord2()
    with assert_raises(FieldNotNullable):
        MyRecord2(None)

@test("pair_of accepts a `default' kwarg")
def _():
    class MyRecord(Record):
        v = pair_of(int, nullable=True, default=(1, 2))
    assert_eq(MyRecord((4, 5)).v, (4, 5))
    assert_eq(MyRecord(None).v, (1, 2))
    assert_eq(MyRecord().v, (1, 2))

#----------------------------------------------------------------------------------------------------------------------------------
# set_of

@test('set_of fields can be defined using any iterable')
def _():
    class MyIterable(object):
        def __iter__(self):
            for i in (1, 2, 3):
                yield i
    class MyRecord(Record):
        elems = set_of(int)
    r = MyRecord(elems=MyIterable())
    assert_eq(r.elems, frozenset([1, 2, 3]))

@test('set_of fields are frozenset instances, and therefore immutable')
def _():
    class MyRecord(Record):
        elems = set_of(int)
    r = MyRecord(elems=[1, 2, 3])
    isinstance(r.elems, frozenset)

@test('elements of the set must be of the correct type')
def _():
    class MyRecord(Record):
        elems = set_of(int)
    with assert_raises(FieldTypeError):
        MyRecord(elems=['1', '2', '3'])

@test("Two sets can use types of the same name, they won't clash")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class Record1(Record):
        elems = set_of(MyClass1)
    class Record2(Record):
        elems = set_of(MyClass2)
    r1 = Record1(elems=[MyClass1()])
    r2 = Record2(elems=[MyClass2()])
    assert_eq(r1.elems.__class__.__name__, 'ElementSet')
    assert_eq(r2.elems.__class__.__name__, 'ElementSet')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two sets use types of the same name, you still can't put one's elems in the other")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class MyRecord(Record):
        elems = set_of(MyClass1)
    with assert_raises(FieldTypeError):
        MyRecord(elems=[MyClass2()])

@test('a nullable set can be null')
def _():
    class MyRecord(Record):
        v = nullable(set_of(int))
    s = MyRecord(None)
    assert_is(s.v, None)

@test('set_of types can be defined using the Field class')
def _():
    class MyRecord(Record):
        v = set_of(Field(int))
    assert_eq(MyRecord({1, 2, 3}).v, {1, 2, 3})

@test("set_of accepts a `coerce' kwarg")
def _():
    class MyRecord(Record):
        v = set_of(
            int,
            coerce=lambda v: map(int, v),
        )
    assert_eq(
        MyRecord('123').v,
        {1, 2, 3},
    )

@test("set_of accepts a `check' kwarg")
def _():
    class MyRecord(Record):
        v = set_of(
            int,
            check=lambda s: len(s) == 3,
        )
    assert_eq(MyRecord({1, 2, 3}).v, {1, 2, 3})
    with assert_raises(FieldValueError):
        MyRecord({1, 2, 3, 4})

@test("set_of accepts a `nullable' kwarg")
def _():
    class MyRecord1(Record):
        v = set_of(int, nullable=True)
    assert_none(MyRecord1().v)
    assert_none(MyRecord1(None).v)

    class MyRecord2(Record):
        v = set_of(int, nullable=False)
    with assert_raises(TypeError):
        MyRecord2()
    with assert_raises(FieldNotNullable):
        MyRecord2(None)

@test("set_of accepts a `default' kwarg")
def _():
    class MyRecord(Record):
        v = set_of(int, nullable=True, default={1, 2, 3})
    assert_eq(MyRecord({4, 5, 6}).v, {4, 5, 6})
    assert_eq(MyRecord(None).v, {1, 2, 3})
    assert_eq(MyRecord().v, {1, 2, 3})

#----------------------------------------------------------------------------------------------------------------------------------
# dict_of

@test('dict_of fields can be defined using a dict')
def _():
    class MyRecord(Record):
        elems = dict_of(int, text_type)
    r = MyRecord(elems={1:'uno', 2:'zwei'})
    assert_eq(r.elems, {1:'uno', 2:'zwei'})

@test('dict_of fields can be defined using an iterator of key/value pairs')
def _():
    class MyRecord(Record):
        elems = dict_of(int, text_type)
    r = MyRecord(elems=(iter([[1, 'uno'], [2, 'zwei']])))
    assert_eq(r.elems, {1:'uno', 2:'zwei'})

@test('keys of the dict must be of the correct type')
def _():
    class MyRecord(Record):
        elems = dict_of(int, text_type)
    with assert_raises(FieldTypeError):
        MyRecord(elems={'1': 'uno'})

@test('values of the dict must be of the correct type')
def _():
    class MyRecord(Record):
        elems = dict_of(int, text_type)
    with assert_raises(FieldTypeError):
        MyRecord(elems={1:1})

@test('dict_of fields are ImmutableDict instances, and therefore immutable')
def _():
    class MyRecord(Record):
        elems = dict_of(int, text_type)
    r = MyRecord(elems={1: 'uno', 2: 'zwei'})
    assert isinstance(r.elems, ImmutableDict)

@test("Two dicts can use types of the same name, they won't clash")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class Record1(Record):
        elems = dict_of(int, MyClass1)
    class Record2(Record):
        elems = dict_of(int, MyClass2)
    r1 = Record1(elems={9:MyClass1()})
    r2 = Record2(elems={9:MyClass2()})
    assert_eq(r1.elems.__class__.__name__, 'IntToElementDict')
    assert_eq(r2.elems.__class__.__name__, 'IntToElementDict')
    assert r1.elems.__class__ is not r2.elems.__class__

@test("If two dicts use types of the same name, you still can't put one's elems in the other")
def _():
    MyClass1 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    MyClass2 = type(native_string('Element'), (object,), {})  # pylint: disable=invalid-name
    class MyRecord(Record):
        elems = dict_of(int, MyClass1)
    with assert_raises(FieldTypeError):
        MyRecord(elems={9:MyClass2()})

@test('dict_of params can be field defs themselves')
def _():
    class MyRecord(Record):
        elems = dict_of(
            text_type,
            pair_of(int),
        )
    with assert_raises(FieldTypeError):
        MyRecord({object(): (1, 2)})
    with assert_raises(FieldValueError):
        MyRecord({'ABC': (1, 2, 3)})
    assert_eq(
        MyRecord({'ABC':(1, 2)}).elems,
        {'ABC': (1, 2)},
    )

@test('a nullable dict can be null')
def _():
    class MyRecord(Record):
        v = nullable(dict_of(int, int))
    s = MyRecord(None)
    assert_is(s.v, None)

@test('dict_of types can be defined using the Field class')
def _():
    class MyRecord(Record):
        v = dict_of(Field(int), Field(int))
    assert_eq(MyRecord({1:1, 2:2, 3:3}).v, {1:1, 2:2, 3:3})

@test("dict_of accepts a `coerce' kwarg")
def _():
    class MyRecord(Record):
        v = dict_of(
            int,
            int,
            coerce=lambda v: {int(i):int(i) for i in v},
        )
    assert_eq(
        MyRecord('123').v,
        {1:1, 2:2, 3:3},
    )

@test("dict_of accepts a `check' kwarg")
def _():
    class MyRecord(Record):
        v = dict_of(
            int,
            int,
            check=lambda s: len(s) == 3,
        )
    assert_eq(MyRecord({1:1, 2:2, 3:3}).v, {1:1, 2:2, 3:3})
    with assert_raises(FieldValueError):
        MyRecord({1:1, 2:2, 3:3, 4:4})

@test("dict_of accepts a `nullable' kwarg")
def _():
    class MyRecord1(Record):
        v = dict_of(int, int, nullable=True)
    assert_none(MyRecord1().v)
    assert_none(MyRecord1(None).v)
    class MyRecord2(Record):
        v = dict_of(int, int, nullable=False)
    with assert_raises(TypeError):
        MyRecord2()
    with assert_raises(FieldNotNullable):
        MyRecord2(None)

@test("dict_of accepts a `default' kwarg")
def _():
    class MyRecord(Record):
        v = dict_of(
            int,
            int,
            nullable=True,
            default={1:1, 2:2, 3:3},
        )
    assert_eq(MyRecord({4:4, 5:5, 6:6}).v, {4:4, 5:5, 6:6})
    assert_eq(MyRecord(None).v, {1:1, 2:2, 3:3})
    assert_eq(MyRecord().v, {1:1, 2:2, 3:3})

#----------------------------------------------------------------------------------------------------------------------------------
# ImmutableDict

@test("ImmutableDict objects are immutable, and therefore you can't assign to their keys")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(TypeError):
        elems[2] = 'two'  # pylint: disable=unsupported-assignment-operation
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't delete their keys")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(TypeError):
        del elems[2]  # pylint: disable=unsupported-delete-operation
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .clear() on them")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(AttributeError):
        elems.clear()
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .pop() on them")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(AttributeError):
        elems.pop(1)
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .popitem() on them")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(AttributeError):
        elems.popitem()
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .setdefault() on them")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(AttributeError):
        elems.setdefault(3, 'trois')
    assert_eq(elems, {1:'uno', 2:'zwei'})

@test("ImmutableDict objects are immutable, and therefore you can't call .update() on them")
def _():
    elems = ImmutableDict({1:'uno', 2:'zwei'})
    with assert_raises(AttributeError):
        elems.update({3: 'trois'})
    assert_eq(elems, {1:'uno', 2:'zwei'})

#----------------------------------------------------------------------------------------------------------------------------------

@test('The type of the elements of a seq_of is accessible')
def _():
    class MyClass(object):
        pass
    class MyRecord(Record):
        v = seq_of(MyClass)
    assert_is(MyRecord.record_fields['v'].type.element_field.type, MyClass)

@test('The type of the elements of a pair_of is accessible')
def _():
    class MyClass(object):
        pass
    class MyRecord(Record):
        v = pair_of(MyClass)
    assert_is(MyRecord.record_fields['v'].type.element_field.type, MyClass)

@test('The type of the elements of a set_of is accessible')
def _():
    class MyClass(object):
        pass
    class MyRecord(Record):
        v = set_of(MyClass)
    assert_is(MyRecord.record_fields['v'].type.element_field.type, MyClass)

@test('The type of the keys and values of a dict_of are accessible')
def _():
    class MyClass1(object):
        pass
    class MyClass2(object):
        pass
    class MyRecord(Record):
        v = dict_of(MyClass1, MyClass2)
    assert_is(MyRecord.record_fields['v'].type.key_field.type, MyClass1)
    assert_is(MyRecord.record_fields['v'].type.value_field.type, MyClass2)

#----------------------------------------------------------------------------------------------------------------------------------

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
from cStringIO import StringIO
from collections import namedtuple
import json
import re

# saintamh
from saintamh.util.lang import Undef

# this module
from .. import *
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------
# sanity

@test("scalar fields are directly rendered to JSON")
def _():
    R = record ('R', id=str, label=unicode, age=int, salary=float)
    r = R (id='robert', label=u"Robert Smith", age=42, salary=12.70)
    j = json.loads(r.json_dumps())
    assert_eq (j, {
        "id": "robert",
        "label": "Robert Smith",
        "age": 42,
        "salary": 12.70,
    })

@test("nested records are rendered to JSON as nested objects")
def _():
    Name = record ('Name', first=unicode, last=unicode)
    Person = record ('Person', name=Name, age=int)
    p = Person (name=Name(first=u"Robert",last=u"Smith"), age=100)
    j = json.loads(p.json_dumps())
    assert_eq (j, {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    })

@test("json_dumps always creates str objects, never unicode")
def _():
    R = record ('R', v=unicode)
    s = R(u"Herv\u00E9").json_dumps()
    assert_isinstance (s, str)

#----------------------------------------------------------------------------------------------------------------------------------
# type-sepcific tests

@foreach (
    (cls_name, cls, val, nullable_or_not, mutator_descr, mutator_func)
    for cls_name,cls,non_null_val in (
        ('str', str, '\xE2\x9C\x93'),
        ('unicode', unicode, u'Herv\u00E9'),
        ('int', int, 42),
        ('long', long, 42L),
        ('float', float, 0.3),
        ('sequence (nonempty)', seq_of(int), (1,2,3)),
        ('sequence (empty)', seq_of(int), []),
        ('set (nonempty)', set_of(int), (1,2,3)),
        ('set (empty)', set_of(int), []),
        ('dict (nonempty)', dict_of(str,int), {'one':1,'two':2}),
        ('dict (empty)', dict_of(str,int), []),
        (lambda R2: ('other record', R2, R2(2)))(record ('R2', v=int)),
    )
    for nullable_or_not,vals in (
        (lambda f: f, (non_null_val,)),
        (nullable, (non_null_val,None)),
    )
    for mutator_descr,mutator_func in sorted (dict.iteritems ({
        'as-is': lambda s: s,
        'w/ spaces everywhere': lambda s: re.sub (r'(?:(?<=[,:\{\[\]\}])|(?=[,:\{\[\]\}]))', ' ', s),
        'w/out spaces': lambda s: re.sub (r'\s+', '', s),
    }))
    for val in vals
)
def _(cls_name, cls, val, nullable_or_not, mutator_descr, mutator_func):

    @test("Record with {}{} field (set to {!r}) -> JSON obj -> str {} -> JSON obj -> Record".format(
        'nullable ' if nullable_or_not is nullable else '',
        cls_name,
        val,
        mutator_descr,
    ))
    def _():
        R = record ('R', field=nullable_or_not(cls))
        r1 = R(val)
        j = mutator_func(r1.json_dumps())
        assert_isinstance (j, str)
        try:
            r2 = R.json_loads (j)
        except Exception:
            print
            print "JSON str: %r" % j
            raise
        assert_eq (r1.field, r2.field)

#----------------------------------------------------------------------------------------------------------------------------------
# duck-typing which classes can be serialized to JSON

@test("the nested object can be anything with a `json_dump' method")
def _():
    class Name (object):
        def __init__ (self, first, last):
            self.first = first
            self.last = last
        def json_dump (self, fh):
            fh.write ('{"first":"%s", "last":"%s"}' % (self.first, self.last))
    Person = record ('Person', name=Name, age=int)
    p = Person (name=Name(first=u"Robert",last=u"Smith"), age=100)
    j = json.loads(p.json_dumps())
    assert_eq (j, {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    })

@test("If a class has a member with no `json_dump' method, it can still be instantiated, but it can't be serialized to JSON")
def _():
    Name = namedtuple ('Name', ('name',))
    R = record ('R', name=Name)
    r = R(Name('peter'))
    with expected_error(CannotBeSerializedToJson):
        buf = StringIO()
        r.json_dump(buf)

#----------------------------------------------------------------------------------------------------------------------------------
# duck-typing which classes can be deserialized from JSON

@test("anything with a `json_scan' method can be parsed from JSON")
def _():
    class Age (namedtuple('Age',('value',))):
        def __init__ (self, value):
            super(Age,self).__init__ (value)
            assert isinstance(value,int) and 0 <= value < 10, repr(value)
        @classmethod
        def json_scan (cls, json_str, pos):
            return Age(int(json_str[pos])), pos+1
    R = record ('R', age=Age)
    assert_eq (
        R.json_loads ('{"age": 9}'),
        R(Age(9)),
    )

@test("If a class has a member with no `json_scan' method, it can still be instantiated, but it can't be parsed from JSON")
def _():
    Name = namedtuple ('Name', ('name',))
    R = record ('R', name=Name)
    r = R(Name('peter'))
    with expected_error(CannotParseJson):
        # using Undef here to ensure that the given value isn't even looked at in any way
        R.json_loads(Undef)

#----------------------------------------------------------------------------------------------------------------------------------
# collections

@test("sequence fields get serialized to JSON lists")
def _():
    R = record ('R', elems=seq_of(int))
    r = R(elems=[1,2,3])
    assert_eq (json.loads(r.json_dumps()), {
        "elems": [1,2,3],
    })

@test("pair fields get serialized to JSON lists")
def _():
    R = record ('R', elems=pair_of(int))
    r = R(elems=[1,2])
    assert_eq (json.loads(r.json_dumps()), {
        "elems": [1,2],
    })

@test("set_of fields get serialized to JSON lists")
def _():
    R = record ('R', elems=set_of(int))
    r = R(elems=[1,2,3])
    json_elems = json.loads(r.json_dumps())['elems']
    assert isinstance (json_elems, list), repr(json_elems)
    assert_eq (
        sorted(json_elems),
        [1,2,3],
    )

@test("dict_of fields get serialized to JSON objects")
def _():
    R = record ('R', elems=dict_of(str,int))
    r = R(elems={'uno':1,'zwei':2})
    try:
        assert_eq (json.loads(r.json_dumps()), {
            "elems": {'uno':1,'zwei':2},
        })
    except Exception:
        print r.json_dumps()
        raise

@test("an empty dict gets serialized to '{}'")
def _():
    R = record ('R', v=dict_of(str,str))
    assert_eq (json.loads(R({}).json_dumps()), {
        'v': {},
    })

@test("dicts with non-string keys cannot be serialized to JSON")
def _():
    R = record ('R', v=dict_of(int,str))
    with expected_error(CannotBeSerializedToJson):
        R({}).json_dumps()

#----------------------------------------------------------------------------------------------------------------------------------
# parser robustness

@test("if the input contains trailing data after a valid JSON object, that raises an exception")
def _():
    R = record ('R', v=dict_of(str,int))
    json_str = '{"v":{"ten":10}}'
    parsed_obj = R({'ten':10})
    assert_eq (R.json_loads(json_str), parsed_obj)
    with expected_error(JsonDecodingError):
        R.json_loads (json_str + '123')

@test("the input may contain trailing spaces, though")
def _():
    R = record ('R', v=dict_of(str,int))
    json_str = '{"v":{"ten":10}}'
    parsed_obj = R({'ten':10})
    assert_eq (R.json_loads(json_str), parsed_obj)
    assert_eq (R.json_loads(json_str+'  \n\t '), parsed_obj)

#----------------------------------------------------------------------------------------------------------------------------------
# handling of null values

@test("null fields are simply not included in the JSON")
def _():
    R = record ('R', x=int, y=nullable(int))
    r = R (x=1, y=None)
    j = json.loads(r.json_dumps())
    assert_eq (j, {'x':1})

@test("explicit 'null' values can be parsed, though")
def _():
    R = record ('R', x=int, y=nullable(int))
    r0 = R(11)
    r1 = R.json_load (StringIO('{"x":11}'))
    r2 = R.json_load (StringIO('{"x":11,"y":null}'))
    assert_eq (r1, r0)
    assert_eq (r2, r0)
    assert_eq (r1, r2)

@test("if the field is not nullable, FieldNotNullable is raised when parsing an explicit 'null'")
def _():
    R = record ('R', x=int, y=int)
    with expected_error(FieldNotNullable):
        R.json_load (StringIO('{"x":11,"y":null}'))

@test("if the field is not nullable, FieldNotNullable is raised when parsing an implicit 'null'")
def _():
    R = record ('R', x=int, y=int)
    with expected_error(FieldNotNullable):
        R.json_load (StringIO('{"x":11}'))

#----------------------------------------------------------------------------------------------------------------------------------
# character escaping in the JSON data

@test("unicode strings with funny characters get correctly escaped as \uXXXX sequences")
def _():
    R = record ('R', label=unicode)
    r1 = R(u"Herv\u00E9")
    json_str = r1.json_dumps()
    assert_eq (json_str, '{"label": "Herv\u00e9"}')
    assert_eq (r1, R.json_loads(json_str))

@test("str objects that contain UTF-8 stay as bytes (unlike in the standard JSON module, which auto-converts)")
def _():
    R = record ('R', label=str)
    r1 = R(u"Herv\u00E9".encode('UTF-8'))
    json_str = r1.json_dumps()
    assert_eq (json_str, '{"label": "Herv\\u00c3\\u00a9"}')
    assert_eq (r1, R.json_loads(json_str))

@foreach (
    (special_char, string_cls)
    for special_char in ('"', '\n', '\r')
    for string_cls in (str, unicode)
)
def _(special_char, string_cls):

    @test("{!r} chars get properly escaped in {} fields".format (special_char, string_cls.__name__))
    def _():
        R = record ('R', label=string_cls)
        r1 = R(string_cls(special_char))
        json_str = r1.json_dumps()
        assert_eq (json_str, '{"label": "\\u%04x"}' % ord(special_char))
        assert_eq (R.json_loads(json_str), r1)

#----------------------------------------------------------------------------------------------------------------------------------
# custom marshallers

@test("fields can be serialized and deserialized using custom marshallers")
def _():
    Point = namedtuple ('Point', ('x','y'))
    marshaller = Marshaller (
        lambda pt: '%d,%d' % pt,
        lambda s: Point(*map(int,s.split(','))),
    )
    with temporary_marshaller_registration (Point, marshaller):
        R = record ('R', pt=Point)
        r1 = R(Point(1,2))
        assert_eq (
            r1.json_dumps(),
            '{"pt": "1,2"}',
        )
        assert_eq (
            R.json_loads(r1.json_dumps()),
            r1,
        )

@test("the marshaller must be available when the class is compiled, not when json_dumps() is called")
def _():
    Point = namedtuple ('Point', ('x','y'))
    marshaller = Marshaller (
        lambda pt: '%d,%d' % pt,
        lambda s: Point(*map(int,s.split(','))),
    )
    R = record ('R', pt=Point)
    with expected_error(CannotBeSerializedToJson):
        R(Point(1,2)).json_dumps()

#----------------------------------------------------------------------------------------------------------------------------------
# pathological cases

@foreach ((
    ('{"id":10', "missing closing mustache"),
    ('{"id" 10}', "missing colon"),
    ('{"id",10}', "comma instead of colon"),
    ('{"id:10}', "missing closing quote"),
    ('{"id":10,"id":11}', "duplicated key"),
    ('{"id":10,,}', "repeated commas"),
    ('{"id":10 "extra":12}', "missing comma"),
))
def _(invalid_json_str, reason):

    @test("JSON parsing of record objects raises an exception for {}".format(reason))
    def _():
        R = record ('R', id=int, extra=nullable(int))
        with expected_error(JsonDecodingError):
            R.json_loads (invalid_json_str)

@foreach ((
    ('{"vals":[1,2,3}', "missing closing square"),
    ('{"vals":[1,,2,3]}', "repeated commas"),
    ('{"vals":[1,2 3]}', "missing comma"),
))
def _(invalid_json_str, reason):

    @test("JSON parsing of seq objects raises an exception for {}".format(reason))
    def _():
        R = record ('R', vals=seq_of(int))
        with expected_error(JsonDecodingError):
            R.json_loads (invalid_json_str)

@foreach ((
    ('{"items":{"a":1, "b":2}', "missing closing mustache"),
    ('{"items" {"a":1, "b" 2}}', "missing colon"),
    ('{"items",{"a":1, "b",2}}', "comma instead of colon"),
    ('{"items:{"a":1, "b:2}}', "missing closing quote"),
    ('{"items":{"a":1, "a":2, "b":2}}', "duplicated key"),
    ('{"items":{"a":1,, "b":2}}', "repeated commas"),
    ('{"items":{"a":1 "b":2} "extra":12}', "missing comma"),
))
def _(invalid_json_str, reason):

    @test("JSON parsing of dict objects raises an exception for {}".format(reason))
    def _():
        R = record ('R', items=dict_of(str,int))
        with expected_error(JsonDecodingError):
            R.json_loads (invalid_json_str)

#----------------------------------------------------------------------------------------------------------------------------------
# TODO

# * Decimal fields are serialized to JSON as strings

#----------------------------------------------------------------------------------------------------------------------------------

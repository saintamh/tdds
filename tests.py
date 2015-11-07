#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id: $
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from collections import Counter
from functools import wraps

# this module
from .record import FieldCheckFailed, FieldIsNotNullable, Field, RecordsAreImmutable, nullable, record

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

def should_raise (exc_type):
    def make_func (func):
        @wraps(func)
        def wrapped_func (*args, **kwargs):
            try:
                func (*args, **kwargs)
            except exc_type:
                return None
            except Exception, ex:
                raise TestFailure ("Raised %s instead of %s" % (ex.__class__.__name__, exc_type.__name__))
            else:
                raise TestFailure ("Expected %s, no exception raised" % exc_type.__name__)
        return wrapped_func
    return make_func

#----------------------------------------------------------------------------------------------------------------------------------

@test('records are immutable')
@should_raise(RecordsAreImmutable)
def _():
    R = record ('R', id = int)
    r = R(10)
    r.id = 11

#----------------------------------------------------------------------------------------------------------------------------------
# numeric fields

def val_type_tests (val_type):
    val_type_name = val_type.__name__

    @test("non-nullable {} fields can't be None".format(val_type_name))
    @should_raise(FieldIsNotNullable)
    def _():
        R = record ('R', id=val_type)
        R(id=None)

    @test("non-nullable {} fields can be zero".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        v = val_type(0)
        r = R(id=v)
        assert r.id == v

    @test("nullable {} fields can be None".format(val_type_name))
    def _():
        R = record ('R', id=nullable(val_type))
        r = R(id=None)
        assert r.id is None

    @test("{} fields can be defined with just the type".format(val_type_name))
    def _():
        R = record ('R', id=val_type)
        r = R(id=val_type(1))

    @test("{} fields defined with just the type are not nullable".format(val_type_name))
    @should_raise(FieldIsNotNullable)
    def _():
        R = record ('R', id=val_type)
        R(id=None)

for val_type in (int,long,float,str,unicode):
    # they need to be within their own scope for the `val_type' to be properly set
    val_type_tests (val_type)

#----------------------------------------------------------------------------------------------------------------------------------

# seq_of, dict_of, pair_of

# nonnegative etc

# types ref'ed by name (e.g. for a LinkedList's "next")

#----------------------------------------------------------------------------------------------------------------------------------
# JSON serialization

@test("scalar fields are directly rendered to JSON")
def _():
    R = record ('R', id=str, label=unicode)
    r = R (id='robert', label=u"Robert Smith")
    j = r.json_struct()
    assert j == {
        "id": "robert",
        "label": "Robert Smith",
    }, repr(j)

@test("nested records are rendered to JSON as nested objects")
def _():
    Name = record ('Name', first=unicode, last=unicode)
    Person = record ('Person', name=Name, age=int)
    p = Person (name=Name(first=u"Robert",last=u"Smith"), age=100)
    j = p.json_struct()
    assert j == {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    }

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
    assert j == {
        "name": {
            "first": "Robert",
            "last": "Smith",
        },
        "age": 100,
    }

#----------------------------------------------------------------------------------------------------------------------------------
# "coerce" functions

@test("a 'coerce' function specified as a lambda can modify the value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: s.upper(),
    ))
    r = R('a')
    assert r.id == 'A'

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
    assert r.id == 'A'

@test("a 'coerce' function specified as a string can modify the value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = '{}.upper()',
    ))
    r = R('a')
    assert r.id == 'A'

@test("the 'coerce' function is invoked before the null check and therefore may get a None value")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = str,
    ))
    r = R(None)
    assert r.id == 'None'

@test("the 'coerce' function may not return None if the field is not nullable")
@should_raise(FieldIsNotNullable)
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: None,
    ))
    r = R('a')

@test("the 'coerce' function may return None if the field is nullable")
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: None,
        nullable = True,
    ))
    r = R('a')
    assert r.id is None

@test("specifying something other than a string or a callable as 'coerce' raises a TypeError")
@should_raise(TypeError)
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = 0,
    ))

@test("the coercion function must return a value of the correct type")
@should_raise(TypeError)
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda v: 10,
    ))
    R(id='not ten')

@test("is the field is not nullable, the coercion function may not return None")
@should_raise(FieldIsNotNullable)
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda v: None,
    ))
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
    assert r.id == 'LOWER'

#----------------------------------------------------------------------------------------------------------------------------------
# 'check' function

@test("if the 'check' function returns False, a FieldCheckFailed exception is raised")
@should_raise(FieldCheckFailed)
def _():
    R = record ('R', id=Field (
        type = str,
        check = lambda s: s == 'valid',
    ))
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
@should_raise(BufferError)
def _():
    def not_none (value):
        if value is None:
            raise BufferError()
    R = record ('R', id=Field (
        type = str,
        coerce = not_none,
    ))
    r = R(None)

@test("the 'check' function may raise exceptions, these are not caught and bubble up")
@should_raise(BufferError)
def _():
    def boom (value):
        raise BufferError ('boom')
    R = record ('R', id=Field (
        type = str,
        check = boom,
    ))
    r = R('a')

@test("specifying something other than a string or a callable as 'check' raises a TypeError")
@should_raise(TypeError)
def _():
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
    assert r2.id == 'OK'

@test("the output of the coercion function is passed to the check function, which may reject it")
@should_raise(FieldCheckFailed)
def _():
    R = record ('R', id=Field (
        type = str,
        coerce = lambda s: s.lower(),
        check = lambda s: s == s.upper(),
    ))
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
        assert r2 == r1

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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# this module
from .. import *
from .plumbing import *

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS,test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

for protocol in (0,1,2,-1):

    @test("records can be pickled and unpickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        class R(Record):
            id = int
            label = unicode
        r1 = R(id=1, label=u"uno")
        r2 = pickle.loads(pickle.dumps(r1, protocol=protocol))
        assert_eq(r2, r1)

    @test("records with sequence fields can be pickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        class R(Record):
            elems = seq_of(pair_of(int))
        r1 = R(elems=((1,2),(3,4)))
        r2 = pickle.loads(pickle.dumps(r1, protocol=protocol))
        assert_eq(r2, r1)

    @test("records with set fields can be pickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        class R(Record):
            elems = set_of(int)
        r1 = R(elems=((1,2,3)))
        r2 = pickle.loads(pickle.dumps(r1, protocol=protocol))
        assert_eq(r2.elems, r1.elems)

    @test("records with dict fields can be pickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        class R(Record):
            elems = dict_of(str,str)
        r1 = R(elems={'a':'alpha','b':'beta'})
        r2 = pickle.loads(pickle.dumps(r1, protocol=protocol))
        assert_eq(r2, r1)

    @test("nested records can be pickled with protocol {:d}".format(protocol))
    def _():
        import pickle
        class RA(Record):
            v = int
        class RB(Record):
            v = RA
        r1 = RB(RA(11))
        r2 = pickle.loads(pickle.dumps(r1, protocol=protocol))
        assert_eq(r2, r1)

#----------------------------------------------------------------------------------------------------------------------------------

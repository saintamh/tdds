#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id: coll.py 3161 2017-03-03 20:42:29Z herve $
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------

class ImmutableDict(object):
    # This is a copy of saintamh.util.coll.ImmutableDict

    def __init__(self, *args, **kwargs):
        self.__impl = dict(*args, **kwargs)

    def __getitem__(self, key):
        return self.__impl.__getitem__(key)

    def __iter__(self):
        return self.__impl.__iter__()

    def __len__(self):
        return self.__impl.__len__()

    def __contains__(self, key):
        return self.__impl.__contains__(key)

    def keys(self):
        return self.__impl.keys()

    def items(self):
        return self.__impl.items()

    def values(self):
        return self.__impl.values()

    def iterkeys(self):
        return self.__impl.iterkeys()

    def iteritems(self):
        return self.__impl.iteritems()

    def itervalues(self):
        return self.__impl.itervalues()

    def get(self, key, **kwargs):
        return self.__impl.get(key, **kwargs)

    def __hash__(self, _cache=[]):
        if not _cache:
            _cache.append(hash(tuple(sorted(self.__impl.iteritems()))))
        return _cache[0]

    def __cmp__(self, other):
        # TODO sth more efficient?
        return cmp(
            tuple(sorted(self.__impl.iteritems())),
            tuple(sorted(other.iteritems())),
        )

#----------------------------------------------------------------------------------------------------------------------------------

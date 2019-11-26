#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    def __hash__(self, _cache=[]):  # pylint: disable=dangerous-default-value
        if not _cache:
            _cache.append(hash(tuple(sorted(self.__impl.items()))))
        return _cache[0]

    @staticmethod
    def __key__(obj):
        # TODO sth more efficient?
        return sorted(obj.items())

    def __eq__(self, other):
        return self.__key__(self) == self.__key__(other)

    def __ne__(self, other):
        return self.__key__(self) != self.__key__(other)

    def __lt__(self, other):
        return self.__key__(self) < self.__key__(other)

    def __le__(self, other):
        return self.__key__(self) <= self.__key__(other)

    def __gt__(self, other):
        return self.__key__(self) > self.__key__(other)

    def __ge__(self, other):
        return self.__key__(self) >= self.__key__(other)

    def __str__(self):
        return str(self.__impl)

    def __repr__(self):
        return repr(self.__impl)

#----------------------------------------------------------------------------------------------------------------------------------

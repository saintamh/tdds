#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import Counter
import re
from sys import argv, exit

# this module
from . import (
    check_tests,
    cleaner_tests,
    coercion_tests,
    collection_tests,
    core_tests,
    marshaller_tests,
    pickle_tests,
    pods_tests,
    readme_tests,
    recursive_types_tests,
    shortcut_tests,
    subclassing_tests,
)

#----------------------------------------------------------------------------------------------------------------------------------

ALL_TEST_MODS = (
    check_tests,
    cleaner_tests,
    coercion_tests,
    collection_tests,
    core_tests,
    marshaller_tests,
    pickle_tests,
    pods_tests,
    readme_tests,
    recursive_types_tests,
    shortcut_tests,
    subclassing_tests,
)

def iter_all_tests(selected_mod_name):
    mod_name = lambda mod: re.sub(r'.+\.', '', re.sub(r'_tests$', '', mod.__name__))
    found = False
    for mod in ALL_TEST_MODS:
        if selected_mod_name in (None, mod_name(mod)):
            found = True
            for test in mod.ALL_TESTS:
                yield test
    if selected_mod_name and not found:
        raise Exception("Module '%s' not found. Available modules:\n%s" % (
            selected_mod_name,
            ''.join(
                '\n\t%s' % mod_name(mod)
                for mod in ALL_TEST_MODS
            ),
        ))

#----------------------------------------------------------------------------------------------------------------------------------

def main(selected_mod_name=None, quick_fail=True):
    tally = Counter()
    all_tests = tuple(iter_all_tests(selected_mod_name))
    test_id_fmt = '{{:.<{width}}}'.format(width=3 + max(len(test_id) for test_id, test_func in all_tests))
    result_fmt = '[{:^4}] {}'
    for test_id, test_func in all_tests:
        tally['total'] += 1
        print(test_id_fmt.format(test_id+' '), end='')
        try:
            test_func()
        except Exception as ex:
            if quick_fail:
                raise
            print(result_fmt.format('FAIL', '{}: {}'.format(ex.__class__.__name__, ex)))
            tally['failed'] += 1
        else:
            print(result_fmt.format('OK', ''))
            tally['passed'] += 1
    print()
    for item in sorted(tally.items()):
        print('{}: {}'.format(*item))
    exit(1 if tally.get('failed') else 0)

if __name__ == '__main__':
    main(*argv[1:])

#----------------------------------------------------------------------------------------------------------------------------------

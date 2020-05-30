#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from doctest import DocTestParser, DocTestRunner
import json
from os import path
import pickle
import re
import sys

# this module
from .plumbing import build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test('Readme file examples are valid')
def t():
    if sys.version_info[0] == 2:
        # This test is disabled in Python2. There are too many subtle differences in the syntax ('str' has to be renamed 'unicode',
        # 'u' prefix is needed in front of string literals, etc), it's too hacky to preserve compatibility.
        #
        # In any case this test isn't to verify that the library works in Python2, it's too check that the README is up to date
        # with the code. So it doesn't matter.
        #
        return

    readme_file_path = path.join(path.dirname(__file__), '..', 'README.md')
    with open(readme_file_path, 'rb') as file_in:
        doctest_str = '\n\n'.join(
            re.findall(
                r'```python\s+(.+?)```',
                file_in.read().decode('UTF-8'),
                flags=re.S,
            ),
        )
    assert doctest_str
    parser = DocTestParser()
    runner = DocTestRunner()
    runner.run(
        parser.get_doctest(
            doctest_str,
            dict(globals(), json=json, pickle=pickle),
            'README.md',
            'README.md',
            0,
        ),
    )
    assert runner.failures == 0

#----------------------------------------------------------------------------------------------------------------------------------

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

# this module
from .plumbing import build_test_registry

#----------------------------------------------------------------------------------------------------------------------------------
# init

ALL_TESTS, test = build_test_registry()

#----------------------------------------------------------------------------------------------------------------------------------

@test('Readme file examples are valid')
def t():
    readme_file_path = path.join(path.dirname(__file__), '..', 'README.md')
    with open(readme_file_path, 'rt', encoding='UTF-8') as file_in:
        doctest_str = '\n\n'.join(re.findall(r'```pycon\s+(.+?)```', file_in.read(), flags=re.S))
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

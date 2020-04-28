#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------

# 2+3 compatibility
from __future__ import unicode_literals

# standards
import setuptools

#----------------------------------------------------------------------------------------------------------------------------------

setuptools.setup(
    name='cargo',
    version='1.0',
    description='Immutable type-checked data structures',
    author='Herv\u00e9 Saint-Amand',
    author_email='cargo@saintamh.org',
    url='https://github.com/saintamh/cargo/',
    packages=setuptools.find_packages(),
)

#----------------------------------------------------------------------------------------------------------------------------------

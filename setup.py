#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------

# 2+3 compatibility
from __future__ import unicode_literals

# standards
from os import path
import setuptools

#----------------------------------------------------------------------------------------------------------------------------------

with open(path.join(path.dirname(__file__), 'README.md'), 'rb') as file_in:
    long_description = file_in.read().decode('UTF-8')

setuptools.setup(
    name='tdds',
    version='1.0',
    description='Typed, declarative data structures',
    author='Herv\u00e9 Saint-Amand',
    author_email='tdds@saintamh.org',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/saintamh/tdds/',
    packages=setuptools.find_packages(),
    install_requires=[],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ],
)

#----------------------------------------------------------------------------------------------------------------------------------

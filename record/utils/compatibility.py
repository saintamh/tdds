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
from sys import version_info

#----------------------------------------------------------------------------------------------------------------------------------
# globals

PY2 = (version_info[0] == 2)

if PY2:
    text_type = unicode
    bytes_type = str
    string_types = (str, unicode)
    integer_types = (int, long)
else:
    text_type = str
    bytes_type = bytes
    string_types = (bytes, str)
    integer_types = (int,)

#----------------------------------------------------------------------------------------------------------------------------------

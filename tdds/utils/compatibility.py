#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from sys import version_info

#----------------------------------------------------------------------------------------------------------------------------------
# globals

# Sorry about the lowercase globals, pylint: disable=invalid-name
# Also this is full of Python2 globals and modules, pylint: disable=import-error, undefined-variable
# And we don't use them directly in here, they're for importing from other files, pylint: disable=unused-import

PY2 = (version_info[0] == 2)

if PY2:
    import __builtin__ as python_builtins
    text_type = unicode
    bytes_type = str
    string_types = (str, unicode)
    integer_types = (int, long)
else:
    import builtins as python_builtins
    text_type = str
    bytes_type = bytes
    string_types = (bytes, str)
    integer_types = (int,)

native_string = str

#----------------------------------------------------------------------------------------------------------------------------------

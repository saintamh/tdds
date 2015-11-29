#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from cStringIO import StringIO
import json

# saintamh
from ..util.codegen import ExternalValue, SourceCodeTemplate

# this module
from .utils import ExternalCodeInvocation, Joiner

#----------------------------------------------------------------------------------------------------------------------------------
# constants

AUTOCAST_TYPES = {
    # These are types that we know the json codec maps internally, and so we unmap them. For instance if you have a `long' field,
    # it'll become an int in the JSON dict. We need to implicitly accept int values here, and inplicity map them back to `long',
    # else the constructor call will fail.
    long: long,
    str: "{}.encode('UTF-8')",
}

TYPES_THAT_CAN_BE_DUMPED_RAW = frozenset ((int,long,float,bool,None.__class__))

#----------------------------------------------------------------------------------------------------------------------------------

class CannotBeSerializedToJson (ValueError):
    pass

class JsonMethodsTemplate (SourceCodeTemplate):

    template = '''
        def json_dump (self, fh):
            $json_dump_stmts
        def json_dumps (self):
            buf = $StringIO()
            self.json_dump (buf)
            return buf.getvalue()
    '''

    StringIO = ExternalValue(StringIO)

    @property
    def json_dump_stmts (self):
        try:
            return Joiner ('', values=tuple(self.json_dump_stmts_chunks()))
        except CannotBeSerializedToJson, err:
            return 'raise TypeError(%r)' % str(err)

    def write_value (self, fdef, value_expr, value_descr):
        if hasattr (fdef.type, 'json_dump'):
            yield '%s.json_dump(fh)\n' % value_expr
        else:
            if fdef.type in TYPES_THAT_CAN_BE_DUMPED_RAW:
                json_expr = 'str(%s)' % value_expr
            elif issubclass (fdef.type, basestring):
                json_expr = ExternalCodeInvocation (json.encoder.encode_basestring_ascii, value_expr)
            else:
                raise CannotBeSerializedToJson ("%s cannot be serialized to JSON" % value_descr)
            yield 'fh.write ('
            yield json_expr
            yield ')\n'

#----------------------------------------------------------------------------------------------------------------------------------

class JsonMethodsForRecordTemplate (JsonMethodsTemplate):

    def __init__ (self, cls_name, field_defs):
        self.cls_name = cls_name
        self.field_defs = field_defs

    def json_dump_stmts_chunks (self):
        for i,(fname,fdef) in enumerate(sorted(self.field_defs.iteritems())):
            for chunk in self.json_dump_stmts_one_field (i,fname,fdef):
                yield chunk

    def json_dump_stmts_one_field (self, i, fname, fdef):
        prefix = '{' if i == 0 else ', '
        suffix = '}' if i == len(self.field_defs)-1 else None
        yield 'fh.write (\'%s"%s": \')\n' % (prefix,fname)
        for chunk in self.write_value (
                fdef,
                value_expr = 'self.%s' % fname,
                value_descr = '%s.%s' % (self.cls_name, fname),
                ):
            yield chunk
        if suffix:
            yield 'fh.write (\'%s\')\n' % (suffix)

#----------------------------------------------------------------------------------------------------------------------------------

class JsonMethodsForSeqTemplate (JsonMethodsTemplate):

    def __init__ (self, elem_fdef):
        self.elem_fdef = elem_fdef

    def json_dump_stmts_chunks (self):
        yield 'fh.write ("[")\n'
        yield 'for i,e in enumerate(self):\n'
        yield '    if i > 0:\n'
        yield '        fh.write (", ")\n'
        yield '    '
        for chunk in self.write_value (self.elem_fdef, 'e', 'elem'):
            yield chunk
        yield 'fh.write ("]")\n'

class JsonMethodsForDictTemplate (JsonMethodsTemplate):

    def __init__ (self, key_fdef, val_fdef):
        self.key_fdef = key_fdef
        self.val_fdef = val_fdef

    def json_dump_stmts_chunks (self):
        if not issubclass(self.key_fdef.type,basestring):
            raise CannotBeSerializedToJson ('dict_of keys must be str or unicode for JSON serialization')
        yield 'fh.write ("{")\n'
        yield 'for i,(k,v) in enumerate(self.iteritems()):\n'
        yield '    if i > 0:\n'
        yield '        fh.write (", ")\n'
        yield '    '
        for chunk in self.write_value (self.key_fdef, 'k', 'key'):
            yield chunk
        yield '    fh.write (": ")\n'
        yield '    '
        for chunk in self.write_value (self.val_fdef, 'v', 'dict_of value'):
            yield chunk
        yield 'fh.write ("}")\n'

#----------------------------------------------------------------------------------------------------------------------------------

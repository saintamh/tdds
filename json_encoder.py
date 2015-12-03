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
from json.encoder import encode_basestring_ascii
import re

# saintamh
from ..util.codegen import SourceCodeTemplate

# this module
from .utils import Joiner

#----------------------------------------------------------------------------------------------------------------------------------

TYPES_THAT_CAN_BE_DUMPED_RAW = frozenset ((int,long,float,bool,None.__class__))

class CannotBeSerializedToJson (TypeError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class JsonEncoderMethodsTemplate (SourceCodeTemplate):

    template = '''
        def json_dumps (self):
            buf = $StringIO()
            self.json_dump (buf)
            return buf.getvalue()

        def json_dump (self, fh):
            $json_dump
    '''

    re = re
    StringIO = StringIO
    CannotBeSerializedToJson = CannotBeSerializedToJson

    @property
    def json_dump (self):
        try:
            return self.json_dump_method_body
        except CannotBeSerializedToJson, err:
            return 'raise $CannotBeSerializedToJson(%r)' % str(err)

    json_dump_method_body = NotImplemented

    def code_to_write_value_to_fh (self, fdef, value_expr, value_descr):
        if hasattr (fdef.type, 'json_dump'):
            writer_code = SourceCodeTemplate ('$v.json_dump(fh)', v=value_expr)
        elif fdef.type in TYPES_THAT_CAN_BE_DUMPED_RAW:
            writer_code = SourceCodeTemplate ('fh.write(str($v))', v=value_expr)
        elif issubclass (fdef.type, basestring):
            # I'd want to use the standard json.encoder.encode_basestring_ascii here, but it insists on implicity decoding
            # UTF-8 bytes into a unicode string, which is not what I want
            writer_code = SourceCodeTemplate (
                r'''
                    fh.write ('"%s"' % $re.sub (
                        r'[^\ !\#-~]',
                        lambda m: '\\u%04x' % ord(m.group()),
                        $v
                    ))
                ''',
                re = re,
                v = value_expr,
            )
        else:
            raise CannotBeSerializedToJson ("{} (type {}) cannot be serialized to JSON".format(value_descr,fdef.type.__name__))
        if fdef.nullable:
            writer_code = SourceCodeTemplate (
                '''
                    if $v is None:
                        fh.write ("null")
                    else:
                        $rest
                ''',
                v = value_expr,
                rest = writer_code,
            )
        return writer_code

#----------------------------------------------------------------------------------------------------------------------------------

class JsonEncoderMethodsForRecordTemplate (JsonEncoderMethodsTemplate):

    def __init__ (self, cls_name, field_defs):
        self.cls_name = cls_name
        self.field_defs = field_defs

    @property
    def json_dump_method_body (self):
        return Joiner ('', values=tuple(
            SourceCodeTemplate (
                '''
                    fh.write ('$prefix"$fname": ')
                    $write_value
                    $write_suffix
                ''',
                fname = fname,
                prefix = '{' if i == 0 else ', ',
                write_value = self.code_to_write_value_to_fh (
                    fdef,
                    value_expr = 'self.%s' % fname,
                    value_descr = '%s.%s' % (self.cls_name, fname),
                ),
                write_suffix = 'fh.write("}")' if i == len(self.field_defs)-1 else None,
            )
            for i,(fname,fdef) in enumerate(sorted(self.field_defs.iteritems()))
        ))

#----------------------------------------------------------------------------------------------------------------------------------

class JsonEncoderMethodsForSeqTemplate (JsonEncoderMethodsTemplate):

    def __init__ (self, elem_fdef):
        self.elem_fdef = elem_fdef

    @property
    def json_dump_method_body (self):
        return SourceCodeTemplate (
            '''
                fh.write ("[")
                for i,e in enumerate(self):
                    if i > 0:
                        fh.write (", ")
                    $write_value
                fh.write ("]")
            ''',
            write_value = self.code_to_write_value_to_fh (self.elem_fdef, 'e', 'elem'),
        )

#----------------------------------------------------------------------------------------------------------------------------------

class JsonEncoderMethodsForDictTemplate (JsonEncoderMethodsTemplate):

    def __init__ (self, key_fdef, val_fdef):
        self.key_fdef = key_fdef
        self.val_fdef = val_fdef

    @property
    def json_dump_method_body (self):
        if issubclass(self.key_fdef.type,basestring):
            return SourceCodeTemplate (
                '''
                    fh.write ("{")
                    for i,(k,v) in enumerate(self.iteritems()):
                        if i > 0:
                            fh.write (", ")
                        $write_key
                        fh.write (": ")
                        $write_val
                    fh.write ("}")
                ''',
                write_key = self.code_to_write_value_to_fh (self.key_fdef, 'k', 'dict_of key'),
                write_val = self.code_to_write_value_to_fh (self.val_fdef, 'v', 'dict_of value'),
            )
        else:
            return '''
                raise $CannotBeSerializedToJson ('dict_of keys must be str or unicode for JSON serialization')
            '''

#----------------------------------------------------------------------------------------------------------------------------------

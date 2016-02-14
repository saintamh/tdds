#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# 2016-02-13 - on serializing `str' values to JSON

# JSON is meant for strings, not arbitrary binary data, so you have to be careful if you want to encode arbitrary `str' objects,
# which we do. If your str contains only ASCII data then it's easy, but if it contains anything between 0x80 and 0xFF, there's the
# question of how to encode it in JSON. JSON doesn't have Python's "\xFF" escapes.

# I considered sidestepping the whole issue by decreeing that only `str' objects that could be encoded as US-ASCII strings were
# allowed, and that for anything else you had to pre-encode the data, say to base64. But then that could lead to situations where,
# say, you have a scraper that saves URLs to JSON, and it works fine for months, then one day it hits a URL from the wild that has
# a non-ASCII, non-escaped value in it, and then the JSON serializer crashes. That would suck.

# Another option would have been to insert python-style "\xFF" escapes in the data. Then only a program that's aware of the trick
# would be able to parse it. But that would suck because any other program I write to read the JSON (and JSON is great for
# inter-program data exchange) would need a custom JSON parser, which is out of the question.

# What I settled on is a bit of a hack: values between 0x80 and 0xFF are simply encoded as unicode escapes ranging from "\u0080" to
# "\u00FF". This is wrong, in the sense that "\u00FF" means "latin small letter y with diaeresis", but what we're handling here is
# bytes, not characters. A 3rd party program parsing this data would have to make sure they know what they're doing when parsing
# this. This works for us, because we know the type of our fields, but other JSON libs will dutifully parse "\u00FF" as a "y with
# diaeresis", and you'll have to somehow convert that back to a 0xFF byte. It seemed to be the least bad option.

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from cStringIO import StringIO
import re

# saintamh
from ..util.codegen import SourceCodeTemplate

# this module
from .marshaller import lookup_marshalling_code_for_type
from .utils import ExternalCodeInvocation, Joiner

#----------------------------------------------------------------------------------------------------------------------------------

TYPES_THAT_CAN_BE_DUMPED_RAW = frozenset ((int,long,float,bool))

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
        ftype = fdef.type
        if ftype in TYPES_THAT_CAN_BE_DUMPED_RAW:
            writer_code = SourceCodeTemplate ('fh.write(str($v))', v=value_expr)
        elif callable (getattr (ftype, 'json_dump', None)):
            writer_code = SourceCodeTemplate ('$v.json_dump(fh)', v=value_expr)
        else:
            if not issubclass (ftype, basestring):
                marshalling_code = lookup_marshalling_code_for_type (ftype)
                if not marshalling_code:
                    raise CannotBeSerializedToJson ("Cannot serialize {} (type {}) to JSON (try registering a marshaller)".format (
                        value_descr,
                        ftype.__name__,
                    ))
                value_expr = ExternalCodeInvocation (marshalling_code, value_expr)
            # I'd want to use the standard json.encoder.encode_basestring_ascii here, but it insists on implicity decoding
            # UTF-8 bytes into a unicode string, which is not what I want
            writer_code = SourceCodeTemplate (
                # `str' bytes such as 0xFF will be serialized as "\u00FF" -- see comment in header
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
        return writer_code

#----------------------------------------------------------------------------------------------------------------------------------

class JsonEncoderMethodsForRecordTemplate (JsonEncoderMethodsTemplate):

    def __init__ (self, cls_name, field_defs):
        self.cls_name = cls_name
        self.field_defs = field_defs

    @property
    def json_dump_method_body (self):
        return Joiner ('', values=tuple(
            self.stmts_to_write_one_field (i,fname,fdef)
            for i,(fname,fdef) in enumerate(sorted(self.field_defs.iteritems()))
        ))

    def stmts_to_write_one_field (self, i, fname, fdef):
        stmt = SourceCodeTemplate (
            '''
                fh.write ('"$fname": ')
                $write_value
            ''',
            fname = fname,
            write_value = self.code_to_write_value_to_fh (
                fdef,
                value_expr = 'self.%s' % fname,
                value_descr = '%s.%s' % (self.cls_name, fname),
            ),
        )
        if i > 0:
            stmt = SourceCodeTemplate (
                '''
                    fh.write (',')
                    $stmt
                ''',
                stmt = stmt
            )
        if fdef.nullable:
            stmt = SourceCodeTemplate (
                '''
                    if self.$fname is not None:
                        $stmt
                ''',
                fname = fname,
                stmt = stmt
            )
        if i == 0:
            stmt = SourceCodeTemplate (
                '''
                    fh.write ('{')
                    $stmt
                ''',
                stmt = stmt
            )
        if i == len(self.field_defs) - 1:
            stmt = SourceCodeTemplate (
                '''
                    $stmt
                    fh.write("}")
                ''',
                stmt = stmt,
            )
        return stmt

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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
Herve Saint-Amand
Edinburgh
"""

#----------------------------------------------------------------------------------------------------------------------------------
# of reinventing the wheel

# I'm not happy with the amount of manual parsing I've ended up implementing. I would much rather have used the standard `json'
# module, or at least reused more of its innards than I ended up doing. But that module just doesn't fit our model, where we
# already know in advance the structure of the whole tree, and the types of all its values.

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import re

# saintamh
from saintamh.util.codegen import ExternalValue, SourceCodeTemplate

# this module
from .marshaller import lookup_unmarshalling_code_for_type
from .utils import ExternalCodeInvocation, Joiner

#----------------------------------------------------------------------------------------------------------------------------------
# custom exceptions

class CannotParseJson (TypeError):
    """
    Indicates that a given Record class cannot be parsed from JSON (e.g. it has a pointer to an object that we don't know how to
    serialize)
    """

class JsonDecodingError (ValueError):
    """
    Indicates that an error occured while parsing a JSON document (e.g. ill-formed data)
    """

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def preview (s, pos=0):
    s = s[pos:]
    if len(s) > 50:
        return repr(s[:47]) + '...'
    else:
        return repr(s)

#----------------------------------------------------------------------------------------------------------------------------------

class JsonDecoderMethodsTemplate (SourceCodeTemplate):

    template = '''
        @classmethod
        def json_load (cls, fh):
            # FIXME - 2015-11-30 - Ideally I'd like to avoid reading in the whole string to memory. It does make the code an order
            # of magnitude simpler, though. FWIW it's what the Python implementation of the standard module does (not sure about
            # the C implementation, which is what actually runs)
            return cls.json_loads (fh.read())

        @classmethod
        def json_loads (cls, json_str):
            val,end = cls.json_scan (json_str, 0)
            if end != len(json_str):
                raise $JsonDecodingError ("Trailing data: %s" % $preview(json_str,end))
            return val

        @classmethod
        def json_scan (cls, json_str, pos):
            $json_scan
    '''

    preview = ExternalValue(preview)
    CannotParseJson = CannotParseJson
    JsonDecodingError = JsonDecodingError

    @property
    def json_scan (self):
        try:
            return self.json_scan_or_cannot_parse
        except CannotParseJson, err:
            return 'raise $CannotParseJson(%r)' % str(err)

#----------------------------------------------------------------------------------------------------------------------------------

class JsonDecoderMethodsForRecordTemplate (JsonDecoderMethodsTemplate):

    def __init__ (self, field_defs):
        self.field_defs = field_defs

    @property
    def json_scan_or_cannot_parse (self):
        return SourceCodeTemplate (
            '''
                $match_open_curly
                if m.group(1) is None:
                    return None,pos
                constructor_kwargs = {}
                while True:
                    $match_quote_maybe
                    else:
                        break
                    $parse_key
                    if key in constructor_kwargs:
                        raise $JsonDecodingError ("Duplicate key: {!r}".format(key))
                    $match_semicol
                    $parse_value
                    else:
                        raise $JsonDecodingError ("Unknown key %r" % key)
                    constructor_kwargs[key] = decoded_val
                    # NB we allow a comma at the end of an object, unlike strict JSON
                    $match_comma_maybe
                    else:
                        break
                $match_close_curly
                $insert_none_for_missing_values
                return cls(**constructor_kwargs),pos
            ''',
            JsonDecodingError = JsonDecodingError,
            match_open_curly  = code_to_match_json_str (r'\s*(?:(\{)|null)\s*'),
            match_close_curly = code_to_match_json_str (r'\s*\}\s*'),
            match_quote_maybe = code_to_match_json_str (r'(?=\")', allow_mismatch=True),
            parse_key         = code_to_parse_string (str, output_var_name='key'),
            match_semicol     = code_to_match_json_str (r'\s*:\s*'),
            match_comma_maybe = code_to_match_json_str (r'\s*,\s*', allow_mismatch=True),
            parse_value       = self.if_else_branches_to_parse_value(),
            insert_none_for_missing_values = Joiner ('\n', values=(
                # We fill in missing values with None, so that if a value is missing we get a FieldNotNullable exception, not a
                # mysterious TypeError about invalid number of parameters to some unspecified function. We do it after parsing is
                # done, so that we can easily detect duplicated keys.
                SourceCodeTemplate (
                    '''
                        constructor_kwargs.setdefault($key,None)
                    ''',
                    key = ExternalValue(fname),
                )
                for fname in self.field_defs
            )),
        )

    def if_else_branches_to_parse_value (self):
        # NB it's important to use `tuple' on the next line else if you let the expressions be lazy-evaluated we don't properly
        # catch the CannotParseJson exception above
        return Joiner ('', values = tuple (
            SourceCodeTemplate (
                '''
                    $if_or_elif key == $fname:
                        $parse
                ''',
                if_or_elif = 'if' if i == 0 else 'elif',
                fname = ExternalValue(fname),
                parse = code_to_decode_one_field (fdef, fname),
            )
            for i,(fname,fdef) in enumerate(self.field_defs.iteritems())
        ))

#----------------------------------------------------------------------------------------------------------------------------------

class JsonDecoderMethodsForSeqTemplate (JsonDecoderMethodsTemplate):

    def __init__ (self, elem_fdef):
        self.elem_fdef = elem_fdef

    @property
    def json_scan_or_cannot_parse (self):
        return SourceCodeTemplate (
            '''
                $match_open_square
                if m.group(1) is None:
                    return None,pos
                values = []
                while True:
                    $match_close_square_maybe
                        break
                    $parse_value
                    values.append(decoded_val)
                    $match_comma_maybe
                    else:
                        $match_close_square
                        break
                return cls(values),pos
            ''',
            match_open_square        = code_to_match_json_str (r'\s*(?:(\[)|null)\s*'),
            match_comma_maybe        = code_to_match_json_str (r'\s*,\s*', allow_mismatch=True),
            match_close_square       = code_to_match_json_str (r'\s*\]\s*'),
            match_close_square_maybe = code_to_match_json_str (r'\s*\]\s*', allow_mismatch=True),
            parse_value              = code_to_decode_one_field (self.elem_fdef, '[elem]'),
        )

#----------------------------------------------------------------------------------------------------------------------------------

class JsonDecoderMethodsForDictTemplate (JsonDecoderMethodsTemplate):

    def __init__ (self, key_fdef, val_fdef):
        self.key_fdef = key_fdef
        self.val_fdef = val_fdef

    @property
    def json_scan_or_cannot_parse (self):
        return SourceCodeTemplate (
            '''
                $match_open_curly
                if m.group(1) is None:
                    return None,pos
                pairs = {}
                while True:
                    $match_close_curly_maybe
                        break
                    $parse_key
                    if key in pairs:
                        raise $JsonDecodingError ("Duplicate key in dict: {!r}".format(key))
                    $match_semicol
                    $parse_val
                    pairs[key] = decoded_val
                    $match_comma_maybe
                    else:
                        $match_close_curly
                        break
                return cls(pairs),pos
            ''',
            JsonDecodingError       = JsonDecodingError,
            match_open_curly        = code_to_match_json_str (r'\s*(?:(\{)|null)\s*'),
            match_close_curly       = code_to_match_json_str (r'\s*\}\s*'),
            match_close_curly_maybe = code_to_match_json_str (r'\s*\}\s*', allow_mismatch=True),
            match_quote             = code_to_match_json_str (r'"'),
            match_semicol           = code_to_match_json_str (r'\s*:\s*'),
            match_comma_maybe       = code_to_match_json_str (r'\s*,\s*', allow_mismatch=True),
            parse_key               = code_to_parse_string (self.key_fdef.type, output_var_name='key'),
            parse_val               = code_to_decode_one_field (self.val_fdef, '<val>'),
        )

#----------------------------------------------------------------------------------------------------------------------------------
# Generate code to parse all the JSON types, as well as code to parse other, custom types

TYPES_PARSED_BY_REGEX = {
    int: (r'(?:(\d+)|null)', int),
    long: (r'(?:(\d+)|null)', long),
    float: (r'(?:(\d+(?:\.\d+)?)|null)', float),
    bool: (r'(?:(true|false)|null)', {'true':True,'false':False}.__getitem__),
}

def code_to_decode_one_field_from_regex (regex, parse_str):
    return SourceCodeTemplate (
        '''
            $match_value
            val_str = m.group(1)
            decoded_val = $parse_str(val_str) if val_str is not None else None
        ''',
        match_value = code_to_match_json_str (regex),
        parse_str = parse_str,
    )

def code_to_decode_field_having_json_scan_method (ftype):
    return SourceCodeTemplate (
        '''
            decoded_val,pos = $json_scan (json_str, pos)
        ''',
        json_scan = ftype.json_scan,
    )

def code_to_decode_string_field (ftype):
    return SourceCodeTemplate (
        '''
            if json_str[pos:pos+4] == 'null':
                decoded_val,pos = None,pos+4
            else:
                $parse_string
        ''',
        parse_string = code_to_parse_string (
            string_cls = ftype,
            output_var_name = 'decoded_val',
        ),
    )

def code_to_decode_marshalled_type (ftype, descr):
    unmarshalling_code = lookup_unmarshalling_code_for_type (ftype)
    if not unmarshalling_code:
        raise CannotParseJson ("%s (%s) has no unmarshaller and has no `json_scan' method" % (descr, ftype.__name__))
    return SourceCodeTemplate (
        '''
            $decode_string
            decoded_val = $unmarshall
        ''',
        decode_string = code_to_decode_string_field (str),
        unmarshall = ExternalCodeInvocation (
            unmarshalling_code,
            'decoded_val',
        ),
    )

def code_to_decode_one_field (fdef, descr):
    ftype = fdef.type
    if ftype in TYPES_PARSED_BY_REGEX:
        return code_to_decode_one_field_from_regex (*TYPES_PARSED_BY_REGEX[ftype])
    elif callable (getattr (ftype, 'json_scan', None)):
        return code_to_decode_field_having_json_scan_method (ftype)
    elif issubclass (ftype, basestring):
        return code_to_decode_string_field (ftype)
    else:
        return code_to_decode_marshalled_type (ftype, descr)

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def code_to_match_json_str (regex, allow_mismatch=False):
    # Assumes that variables `json_str' and `pos' exist
    if isinstance (regex, basestring):
        regex = re.compile(regex)
    if allow_mismatch:
        return SourceCodeTemplate (
            '''
                m = $match (json_str, pos)
                if m:
                    pos = m.end()            
            ''', # NB we depend on the template ending in this "if", so we can append an "else" to it
            match = regex.match,
        )
    else:
        return SourceCodeTemplate (
            '''
                m = $match (json_str, pos)
                if not m:
                    raise $JsonDecodingError ("Couldn't match /$pattern/ from %s" % (
                        $preview(json_str,pos),
                    ))
                pos = m.end()
            ''',
            JsonDecodingError = JsonDecodingError,
            match = regex.match,
            pattern = re.sub (r'[\\"/]', lambda m: '\\'+m.group(), repr(regex.pattern)[1:-1]),
            preview = preview,
        )
    return stmt

def code_to_parse_string (string_cls, output_var_name):
    # I wish I could use the standard json.decoder's py_scanstring here, but it only returns unicode objects, which is not what we
    # want because we also encode `str' objects as JSON (as detailed in the header for json_encoder.py). So we have to reinvent
    # this wheel, which isn't pretty.
    if not issubclass (string_cls, basestring):
        raise CannotParseJson ("Only dictionaries with string keys can be serialized to JSON")
    re_chunk = r'([^\\\"]*)(\\|"\s*)'
    return SourceCodeTemplate (
        '''
            string_start_pos = pos
            $match_quote_and_first_chunk
            chunk,terminator = m.groups()
            if terminator != '\\\\': # NB double-escaped because this is code as a string. In real code it'd be single escaped
                $output_var_name = chunk
            else:
                # only build an array if you must
                all_chunks = [chunk]
                while terminator == '\\\\': # same remark as above about the escaping. This checks where it's a single backslash.
                    $match_char_value
                    all_chunks.append ($char(int(m.group(1),16)))
                    $match_chunk
                    else:
                        raise $JsonDecodingError ("Unterminated string literal starting at char %d" % string_start_pos)
                    chunk,terminator = m.groups()
                    all_chunks.append(chunk)
                $output_var_name = $empty_string.join(all_chunks)
        ''',
        output_var_name             = output_var_name,
        JsonDecodingError           = JsonDecodingError,
        match_quote_and_first_chunk = code_to_match_json_str (r'\"' + re_chunk),
        match_chunk                 = code_to_match_json_str (re_chunk, allow_mismatch='yes so we can give a better error mesg'),
        match_char_value            = code_to_match_json_str (r'u([0-9a-fA-F]{4})'),
        char                        = {unicode:unichr,str:chr}[string_cls],
        empty_string                = ExternalValue ({unicode:u'',   str:'' }[string_cls]),
    )

#----------------------------------------------------------------------------------------------------------------------------------

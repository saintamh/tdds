#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id: $
Herve Saint-Amand
Edinburgh
"""

# I'm not happy with the amount of manual parsing I've ended up implementing. I would much rather have used the standard `json'
# module, or at least reused more of its innards than I ended up doing. But that module just doesn't fit our model, where we
# already know in advance the structure of the whole tree, and the types of all its values.

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from json.decoder import py_scanstring
import re

# saintamh
from saintamh.util.codegen import ExternalValue, SourceCodeTemplate

#----------------------------------------------------------------------------------------------------------------------------------

class CannotParseJson (TypeError):
    pass

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
                raise ValueError ("Trailing data: %s" % $preview(json_str,end))
            return val

        @classmethod
        def json_scan (cls, json_str, pos):
            $json_scan
    '''

    preview = ExternalValue(preview)
    CannotParseJson = CannotParseJson

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
                    return None,m.end()
                constructor_kwargs = {}
                while True:
                    # NB we will never parse an empty JSON object here, so there will always be a quote
                    $match_quote
                    key,pos = $py_scanstring (json_str, pos)
                    $match_semicol
                    constructor_kwargs[key],pos = $scanner_funcs_by_fname[key](json_str, pos)
                    # NB we allow a comma at the end of an object, unlike strict JSON
                    $match_comma
                    if not m.group(1):
                        break
                $match_close_curly
                return cls(**constructor_kwargs),pos
            ''',
            match_open_curly  = code_to_match_json_str (r'(?:(\{)|null)\s*'),
            match_close_curly = code_to_match_json_str (r'\s*\}\s*'),
            match_quote       = code_to_match_json_str (r'"'),
            match_semicol     = code_to_match_json_str (r'\s*:\s*'),
            match_comma       = code_to_match_json_str (r'\s*(?:(,)\s*|(?=\}))'),
            scanner_funcs_by_fname = {
                fname: scanner_func_for_field(fdef,fname)
                for fname,fdef in self.field_defs.iteritems()
            },
            preview = preview,
            py_scanstring = py_scanstring,
        )

#----------------------------------------------------------------------------------------------------------------------------------

class JsonDecoderMethodsForSeqTemplate (JsonDecoderMethodsTemplate):

    def __init__ (self, elem_fdef):
        self.elem_fdef = elem_fdef

    @property
    def json_scan_or_cannot_parse (self):
        return SourceCodeTemplate (
            '''
                values = []
                $match_open_square
                if m.group(1) is None:
                    return None,m.end()
                while True:
                    val,pos = $scanner (json_str, pos)
                    values.append(val)
                    $match_comma
                    if not m.group(1):
                        break
                $match_close_square
                return cls(values),pos
            ''',
            match_open_square  = code_to_match_json_str (r'(?:(\[)|null)\s*'),
            match_comma        = code_to_match_json_str (r'\s*(?:(,)\s*|(?=\]))'),
            match_close_square = code_to_match_json_str (r'\s*\]\s*'),
            scanner = scanner_func_for_field (self.elem_fdef, '[elem]')
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
                    return None,m.end()
                pairs = {}
                while True:
                    key,pos = $key_scanner_func (json_str, pos)
                    $match_semicol
                    pairs[key],pos = $val_scanner_func (json_str, pos)
                    $match_comma
                    if not m.group(1):
                        break
                $match_close_curly
                return cls(pairs),pos
            ''',
            match_open_curly  = code_to_match_json_str (r'(?:(\{)|null)\s*'),
            match_close_curly = code_to_match_json_str (r'\s*\}\s*'),
            match_quote       = code_to_match_json_str (r'"'),
            match_semicol     = code_to_match_json_str (r'\s*:\s*'),
            match_comma       = code_to_match_json_str (r'\s*(?:(,)\s*|(?=\}))'),
            key_scanner_func  = scanner_func_for_field (self.key_fdef, '<key>'),
            val_scanner_func  = scanner_func_for_field (self.val_fdef, '<val>'),
        )

#----------------------------------------------------------------------------------------------------------------------------------
# a scanner function takes a string of json and an index within that string, checks that it finds a value at that index, and either
# returns the parsed value and the index after the value, or raises an exception. For instance the int scanner looks for digits,
# and returns the parsed `int' instance.

def scanner_func_for_field (fdef, descr):
    types_parsed_by_regex = {
        int: (r'(?:(\d+)|null)', int),
        long: (r'(?:(\d+)|null)', long),
        float: (r'(?:(\d+(?:\.\d+)?)|null)', float),
        bool: (r'(?:(true|false)|null)', {'true':True,'false':False}.__getitem__),
    }

    if hasattr (fdef.type, 'json_scan'):
        scanner = fdef.type.json_scan

    elif fdef.type in types_parsed_by_regex:
        regex_pattern,parse = types_parsed_by_regex[fdef.type]
        regex_match = re.compile(regex_pattern).match
        def scanner (json_str, pos):
            m = regex_match (json_str, pos)
            if not m:
                raise ValueError ("Couldn't match /%s/ against %s" % (
                    regex_pattern,
                    preview(json_str,pos)
                ))
            val_str = m.group(1)
            if val_str is None:
                return None,m.end()
            return parse(val_str),m.end()

    elif issubclass (fdef.type, basestring):
        def scanner (json_str, pos):
            if json_str[pos:pos+4] == 'null':
                val = None
                end = pos+4
            else:
                if pos >= len(json_str) or json_str[pos] != '"':
                    raise ValueError ("Expected opening quote: %s" % preview(json_str,pos))
                val,end = py_scanstring (json_str, pos+1)
                if fdef.type is str:
                    # FIXME - 2015-11-30 - Ugh. I have a unicode string, whose characters are actually byte values. How do I
                    # convert that to bytes?
                    val = ''.join (map (chr, map (ord, val)))
            return val,end

    else:
        raise CannotParseJson ("%s is of a type (%s) that has no `json_scan' method" % (descr, fdef.type.__name__))

    return scanner

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def code_to_match_json_str (regex):
    # Assumes that variables `json_str' and `pos' exist
    if isinstance (regex, basestring):
        regex = re.compile(regex)
    return SourceCodeTemplate (
        '''
            m = $match (json_str, pos)
            if not m:
                raise ValueError ("Couldn't match /%s/ from %s" % (
                    $pattern,
                    $preview(json_str,pos)
                ))
            pos = m.end()
        ''',
        match = regex.match,
        pattern = repr(regex.pattern),
        preview = preview,
    )

#----------------------------------------------------------------------------------------------------------------------------------

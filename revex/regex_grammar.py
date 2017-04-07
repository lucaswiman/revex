from __future__ import unicode_literals

import re
import sys

from parsimonious import Grammar


def double_regex_escape(char):
    # This works around the fact that we're trying to include this as a
    # regex inside a parsimonious grammar, so we escape odd characters to
    # their hex representation rather than just using "\\".
    if re.escape(char) != char:
        return '\\\\x%0.2X' % ord(char)
    else:
        return char


# The collection of "escapable" characters differs between Python 2 and
# Python 3, but is just set to the appropriate constant here for efficiency.
# See revex.tests.test_parser.test_escapable_chars, where it is verified that
# the list is correct.
if sys.version_info < (3, ):
    ESCAPABLE_CHARS = u'ceghijklmopquyzCEFGHIJKLMNOPQRTUVXY!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'  # noqa
    CHARSET_ESCAPABLE_CHARS = 'ceghijklmopquyzABCEFGHIJKLMNOPQRTUVXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'  # noqa
else:
    ESCAPABLE_CHARS = 'ceghijklmopqyzCEFGHIJKLMNOPQRTVXY!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'  # noqa
    CHARSET_ESCAPABLE_CHARS = 'ceghijklmopqyzABCEFGHIJKLMNOPQRTVXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'  # noqa


REGEX = Grammar(r'''
    re = union / concatenation
    lookahead = "(" ("?=" / "?!" / "?<=" / "?<!") re ")"
    union = (concatenation "|")+ concatenation
    concatenation = (lookahead / quantified / repeat_fixed / repeat_range / literal)*
    quantified = literal ~"[*+?]"
    repeat_fixed = literal "{" ~"\d+" "}"
    repeat_range = literal "{" ~"(\d+)?" "," ~"(\d+)?" "}"

    literal =
        comment /
        group /
        character_set /
        escaped_character /
        charclass /
        character

    group = ("(?:" / "(") !("?=" / "?!" / "?<=" / "?<!") re ")"
    comment = "(?#" ("\)" / ~"[^)]")* ")"

    escaped_character =
        escaped_metachar /
        escaped_numeric_character /
        escaped_whitespace
    escaped_metachar = "\\" ~"[.$^\\\\*+()|{}?\\][/]"
    escaped_numeric_character =
        ("\\"  ~"[0-7]{3}") /
        ("\\x" ~"[0-9a-f]{2}"i) /
        ("\\u" ~"[0-9a-f]{4}"i) /
        ("\\U" ~"[0-9a-f]{8}"i)
    escaped_whitespace = "\\" ~"[ntvr]"

    charclass = "\\" ~"[dDwWsS]"
    character = ~"[^$^\\*+()|?]"
    character_set = "[" "^"? set_items "]"
    set_char = escaped_numeric_character / escaped_set_char / ~"[^\\]]"
    escaped_set_char = "\\" ~"[%s]"
    set_items = (range / escaped_numeric_character / escaped_whitespace / escaped_set_char / ~"[^\\]]" )+
    range = set_char  "-" set_char
''' % ''.join(map(double_regex_escape, CHARSET_ESCAPABLE_CHARS)))  # noqa

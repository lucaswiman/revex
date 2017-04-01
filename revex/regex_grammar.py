from __future__ import unicode_literals

import sys

from parsimonious import Grammar


# The collection of "escapable" characters differs between Python 2 and
# Python 3, but is just set to the appropriate constant here for efficiency.
# See revex.tests.test_parser.test_escapable_chars, where it is verified that
# the list is correct.
if sys.version_info < (3, ):
    ESCAPABLE_CHARS = '0abcdefghijklmnopqrstuvwyzCEFGHIJKLMNOPQRTUVXYZ\\!\\"\\#\\$\\%\\&\\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@\\[\\]\\^\\_\\`\\{\\|\\}\\~\\ \\\t\\\n\\\r\\\x0b\\\x0c'  # noqa
else:
    ESCAPABLE_CHARS = '0abcdefghijklmnopqrstvwyzCEFGHIJKLMNOPQRTVXYZ\\!\\"\\#\\$\\%\\&\\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@\\[\\]\\^_\\`\\{\\|\\}\\~\\ \\\t\\\n\\\r\\\x0b\\\x0c'  # noqa


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
    set_items = (range / escaped_set_char / escaped_character / ~"[^\\]]" )+
    range = set_char  "-" set_char
''' % ESCAPABLE_CHARS)  # noqa

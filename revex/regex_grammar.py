from __future__ import unicode_literals

import re
import string

from parsimonious import Grammar


def double_regex_escape(char):
    # This works around the fact that we're trying to include this as a
    # regex inside a parsimonious grammar, so we escape odd characters to
    # their hex representation rather than just using "\\".
    if re.escape(char) != char:
        return '\\\\x%0.2X' % ord(char)
    else:
        return char


# Note: the collection of "escapable" characters differs between different
# versions of python.


def is_char_escapable(char):
    try:
        regex = re.compile(r'^\{char}$'.format(char=char))
    except Exception:
        return False
    return {c for c in string.printable if regex.match(c)} == {char}


def is_char_escapable_in_charsets(char):
    try:
        regex = re.compile(r'^[\{char}]$'.format(char=char))
    except Exception:
        return False
    return {c for c in string.printable if regex.match(c)} == {char}


ESCAPABLE_CHARS = ''.join(filter(is_char_escapable, string.printable))
CHARSET_ESCAPABLE_CHARS = ''.join(filter(is_char_escapable_in_charsets,
                                         string.printable))


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
        escaped_whitespace /
        escaped_metachar /
        escaped_numeric_character
    escaped_metachar = "\\" ~"[%s]"
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
    set_items = (range / charclass / escaped_numeric_character / escaped_whitespace / escaped_set_char / ~"[^\\]]" )+
    range = set_char  "-" set_char
''' % (  # noqa
        ''.join(map(double_regex_escape, ESCAPABLE_CHARS)),
        ''.join(map(double_regex_escape, CHARSET_ESCAPABLE_CHARS)),
    )
)

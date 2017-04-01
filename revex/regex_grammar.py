from __future__ import unicode_literals

import re, string

from parsimonious import Grammar

def is_char_escapable_in_ranges(char):  # type: (str) -> bool
    return not re.compile(r'[\{char}]'.format(char=char)).match('\\')


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
    set_char = escaped_numeric_character / ~"[^\\]]"
    escaped_set_char = ~"\\\\[[\\]-]"
    set_items = (range / escaped_set_char / escaped_character / ~"[^\\]]" )+
    range = set_char  "-" set_char
''')  # noqa

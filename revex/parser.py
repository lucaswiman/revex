from parsimonious import Grammar, NodeVisitor


REGEX = Grammar(r'''
    re = union / concatenation
    union = (concatenation "|")+ concatenation
    concatenation = (star / plus / literal)+
    star = literal "*"
    plus = literal "+"
    literal = group / any / char / positive_set / negative_set
    group = "(" re ")"
    any = "."
    escaped_metachar = "\\" ~"[.$^\\*+\[\]()]"
    char = escaped_metachar / ~"[^.$^\\*+\[\]()]"
    positive_set = "[" set_items "]"
    negative_set = "[^" set_items "]"
    set_char = ~"[^\\]]|\\]"
    set_items = "-"? (range / ~"[^]")+
    range = char "-" set_char
''')

class RegexVisitor(NodeVisitor):
    grammar = REGEX

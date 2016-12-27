# -*- coding: utf-8 -*-
"""
Regex implementation using the Brzozowski derivative.

Loosely inspired by David MacIver's implementation here:
http://www.drmaciver.com/2016/12/proving-or-refuting-regular-expression-equivalence/

See also https://en.wikipedia.org/wiki/Brzozowski_derivative
"""
from __future__ import unicode_literals

import abc
import operator
from functools import reduce, total_ordering

import six
from parsimonious import NodeVisitor, Grammar


@total_ordering
class RegularExpression(six.with_metaclass(abc.ABCMeta)):
    """
    A generalized regular expression, supporting:
        - ∅:               EMPTY
        - ε:               EPSILON
        - Symbol:          Symbol(elem)
        - Union:           R1 | R2
        - Intersection:    R1 & R2
        - Complementation: ~R
        - Concatenation:   R1 + R2
        - Star:            Star(R)
    """
    @classmethod
    def compile(self, regex):
        return RegexVisitor().parse(regex)

    def __add__(self, other):
        return Concatenation(self, other)

    def __and__(self, other):
        return Intersection(self, other)

    def __or__(self, other):
        return Union(self, other)

    def __invert__(self):
        return Complement(self)

    def __mul__(self, repeat):
        return EPSILON if repeat == 0 else reduce(operator.add, [self] * repeat)

    __rmul__ = __mul__

    @abc.abstractproperty
    def accepting(self):
        """
        Whether an end-string is accepted with this regex.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def derivative(self, char):
        raise NotImplementedError

    def match(self, string):
        regex = self
        for char in string:
            regex = regex.derivative(char)
        return regex.accepting

    @property
    def identity_tuple(self):
        return (type(self).__name__, )

    def __hash__(self):
        return hash(self.identity_tuple)

    def __eq__(self, other):
        return type(self) == type(other) and self.identity_tuple == other.identity_tuple

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if not isinstance(other, RegularExpression):
            raise TypeError(type(other))
        return self.identity_tuple < other.identity_tuple


@six.python_2_unicode_compatible
class _Empty(RegularExpression):
    def __new__(cls):
        try:
            return EMPTY
        except NameError:
            return super(_Empty, cls).__new__(cls)

    accepting = False

    def derivative(self, char):
        return EMPTY

    def __str__(self):
        return '∅'

    def __repr__(self):
        return 'EMPTY'


EMPTY = _Empty()


@six.python_2_unicode_compatible
class _Epsilon(RegularExpression):
    def __new__(cls):
        try:
            return EPSILON
        except NameError:
            return super(_Epsilon, cls).__new__(cls)

    accepting = True

    def derivative(self, char):
        return EMPTY

    def __str__(self):
        return 'ε'

    def __repr__(self):
        return 'EPSILON'


EPSILON = _Epsilon()


@six.python_2_unicode_compatible
class Symbol(RegularExpression):
    def __init__(self, char):
        self.char = char

    accepting = False

    def derivative(self, char):
        return EPSILON if char == self.char else EMPTY

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.char)

    def __str__(self):
        return self.char

    def __repr__(self):
        return 'Symbol(%r)' % self.char


@six.python_2_unicode_compatible
class Concatenation(RegularExpression):
    def __new__(cls, left, right):
        if left is EMPTY or right is EMPTY:
            return EMPTY
        elif right is EPSILON:
            return left
        elif left is EPSILON:
            return right
        else:
            return super(Concatenation, cls).__new__(cls)

    def __init__(self, left, right):
        if hasattr(self, 'children'):
            # __init__ is only being called as an artifact of our __new__
            # hacking. Nothing to do, so bail.
            return
        self.children = (left, right)

    @property
    def accepting(self):
        return all(child.accepting for child in self.children)

    def derivative(self, char):
        left, right = self.children
        derivative = left.derivative(char) + right
        if left.accepting:
            return derivative | right.derivative(char)
        else:
            return derivative

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    def __str__(self):
        return '%s%s' % self.children

    def __repr__(self):
        return '%r+%r' % self.children


class Intersection(RegularExpression):
    def __new__(cls, left, right):
        if EMPTY == left or EMPTY == right:
            return EMPTY
        elif EPSILON == left or EPSILON == right:
            if left.accepting and right.accepting:
                return EPSILON
            else:
                return EMPTY
        elif left == right:
            return left
        elif isinstance(left, Symbol):
            return left if right.derivative(left.char).accepting else EMPTY
        elif isinstance(right, Symbol):
            return right if left.derivative(right.char).accepting else EMPTY
        else:
            return super(Intersection, cls).__new__(cls)

    def __init__(self, left, right):
        if hasattr(self, 'children'):
            # __init__ is only being called as an artifact of our __new__
            # hacking. Nothing to do, so bail.
            return
        if left > right:
            left, right = right, left
        self.children = (left, right)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    @property
    def accepting(self):
        return all(child.accepting for child in self.children)

    def derivative(self, char):
        return reduce(operator.and_, (child.derivative(char) for child in self.children))

    def __str__(self):
        return '(%s)&(%s)' % self.children

    def __repr__(self):
        return '(%r)&(%r)' % self.children


class Union(RegularExpression):
    def __new__(cls, left, right):
        if left is EMPTY:
            return right
        elif right is EMPTY:
            return left
        elif left == right:
            return left
        return super(Union, cls).__new__(cls)

    def __init__(self, left, right):
        if hasattr(self, 'children'):
            # __init__ is only being called as an artifact of our __new__
            # hacking. Nothing to do, so bail.
            return
        if left > right:
            left, right = right, left
        self.children = (left, right)

    @property
    def accepting(self):
        return any(child.accepting for child in self.children)

    def derivative(self, char):
        return reduce(operator.or_, (child.derivative(char) for child in self.children))

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    def __str__(self):
        return '(%s)|(%s)' % self.children

    def __repr__(self):
        return '(%r)|(%r)' % self.children


class Complement(RegularExpression):
    def __new__(cls, regex):
        """
        Distribute inwards using De Morgan's laws to get a canonical
        representation.
        """
        if isinstance(regex, Intersection):
            return reduce(operator.or_, (~child for child in regex.children))
        elif isinstance(regex, Union):
            return reduce(operator.and_, (~child for child in regex.children))
        elif isinstance(regex, Complement):
            return regex.regex
        else:
            return super(Complement, cls).__new__(cls)

    def __init__(self, regex):
        if hasattr(self, 'regex'):
            # __init__ is only being called as an artifact of our __new__
            # hacking. Nothing to do, so bail.
            return
        self.regex = regex

    @property
    def accepting(self):
        return not self.regex.accepting

    def derivative(self, char):
        return ~self.regex.derivative(char)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '~(%s)' % self.regex

    def __repr__(self):
        return '~(%r)' % self.regex


class Star(RegularExpression):
    def __new__(cls, regex):
        if regex is EMPTY or regex is EPSILON:
            return regex
        return super(Star, cls).__new__(cls)

    def __init__(self, regex):
        if hasattr(self, 'regex'):
            # __init__ is only being called as an artifact of our __new__
            # hacking. Nothing to do, so bail.
            return
        self.regex = regex

    accepting = True

    def derivative(self, char):
        return self.regex.derivative(char) + self

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '(%s)*' % self.regex

    def __repr__(self):
        return 'Star(%r)' % self.regex


REGEX = Grammar(r'''
    re = union / concatenation
    sub_re = union / concatenation
    union = (concatenation "|")+ concatenation
    concatenation = (star / plus / repeat_fixed / repeat_range / optional / literal)+
    star = literal "*"
    plus = literal "+"
    optional = literal "?"
    repeat_fixed = literal "{" ~"\d+" "}"
    repeat_range = literal "{" ~"(\d+)?" "," ~"(\d+)?" "}"
    literal = group / any / chars / negative_set / positive_set
    group = "(" sub_re ")"
    escaped_metachar = "\\" ~"[.$^\\*+\[\]()|{}?]"
    any = "."
    chars = char+
    char = escaped_metachar / non_metachar
    non_metachar = ~"[^.$^\\*+\[\]()|{}?]"
    positive_set = "[" set_items "]"
    negative_set = "[^" set_items "]"
    set_char = ~"[^\\]]|\\\\]"
    set_items = (range / ~"[^\\]]")+
    range = set_char "-" set_char
''')


class RegexVisitor(NodeVisitor):
    grammar = REGEX

    def visit_re(self, node, children):
        [re] = children
        return re

    def visit_concatenation(self, node, children):
        return reduce(operator.add, [re for [re] in children])

    def visit_group(self, node, children):
        lparen, [re], rparen = children
        return re

    def visit_union(self, node, children):
        disjuncts = []
        # This is sort of ugly; parsimonious returns children as a list
        # of all its left disjuncts (including the | character) and the final one
        # (sans pipe character).
        disjuncts_and_pipes, last_disjunct = children
        for (disjunct, superfluous_pipe) in disjuncts_and_pipes:
            disjuncts.append(disjunct)
        disjuncts.append(last_disjunct)
        return reduce(operator.or_, disjuncts)

    def visit_star(self, node, children):
        re, star_char = children
        return Star(re)

    def visit_plus(self, node, children):
        re, plus_char = children
        return re + Star(re)

    def visit_literal(self, node, children):
        # Why doesn't parsimonious do this for you?
        [child] = children
        return child

    def visit_chars(self, node, children):
        return reduce(operator.add, children)

    def visit_escaped_metachar(self, node, children):
        slash, char = children
        return Symbol(char)

    def visit_any(self, node, children):
        raise NotImplementedError()

    def visit_char(self, node, children):
        child, = children
        return Symbol(child)

    def visit_set_char(self, node, children):
        char = node.text
        if len(char) == 2:
            assert char[0] == '\\', 'Bug! %s' % char
            return char[1]
        return char

    def visit_range(self, node, children):
        start, dash, end = children
        return reduce(
            operator.or_,
            [Symbol(chr(i)) for i in range(ord(start), ord(end) + 1)])

    def visit_set_items(self, node, children):
        items = [
            item if isinstance(item, RegularExpression) else Symbol(item)
            for item, in children]
        return reduce(operator.or_, items)

    def visit_positive_set(self, node, children):
        [lbrac, inner, rbrac] = children
        return inner

    def visit_negative_set(self, node, children):
        [lbrac, inner, rbrac] = children
        return ~inner

    def visit_repeat_fixed(self, node, children):
        regex, lbrac, repeat_count, rbrac = children
        repeat_count = int(repeat_count)
        if repeat_count == 0:
            raise ValueError('Invalid repeat %s' % node.text)
        return regex * repeat_count

    def visit_repeat_range(self, node, children):
        regex, lbrac, min_repeat, comma, max_repeat, rbrac = children
        min_repeat = int(min_repeat or '0')
        max_repeat = None if not max_repeat else int(max_repeat)
        repeated = regex * min_repeat
        opt = [regex * repeat for repeat in range(0, max_repeat - min_repeat + 1)]
        return repeated + opt

    def visit_optional(self, node, children):
        regex, question_mark = children
        return regex | EPSILON

    def generic_visit(self, node, children):
        return children or node.text

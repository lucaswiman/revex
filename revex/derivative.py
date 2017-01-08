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

from .dfa import RegexDFA, DEFAULT_ALPHABET


@total_ordering
class RegularExpression(six.with_metaclass(abc.ABCMeta)):
    """
    A generalized regular expression, supporting:
        - ∅:               EMPTY
        - ε:               EPSILON
        - CharSet:         CharSet(elems)
        - Union:           R1 | R2
        - Intersection:    R1 & R2
        - Complementation: ~R
        - Concatenation:   R1 + R2
        - Star:            Star(R)
    """
    is_atomic = True

    @classmethod
    def compile(self, regex):
        return RegexVisitor().parse(regex)

    def as_dfa(self, alphabet=DEFAULT_ALPHABET):
        return RegexDFA(self, alphabet=alphabet)

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
        if not isinstance(other, RegularExpression):  # pragma: no cover
            raise TypeError(type(other))
        return self.identity_tuple < other.identity_tuple


def parenthesize_str(regex):
    return six.text_type(regex) if regex.is_atomic else '(%s)' % regex


def parenthesize_repr(regex):
    return repr(regex) if regex.is_atomic else '(%r)' % regex


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
class _Dot(RegularExpression):
    """
    Special expression for matching any character.
    """
    def __new__(cls):
        try:
            return DOT
        except NameError:
            return super(_Dot, cls).__new__(cls)

    accepting = False

    def derivative(self, char):
        return EPSILON

    def __str__(self):
        return '.'

    def __repr__(self):
        return 'DOT'


DOT = _Dot()


@six.python_2_unicode_compatible
class Concatenation(RegularExpression):
    def __new__(cls, *children):
        flattened_children = []
        for child in children:
            if isinstance(child, Concatenation):
                for subchild in child.children:
                    flattened_children.append(subchild)
            else:
                flattened_children.append(child)
        children = flattened_children
        if EMPTY in children:
            return EMPTY
        children = tuple(child for child in children if child is not EPSILON)
        if not children:
            return EPSILON
        elif len(children) == 1:
            return children[0]
        else:
            instance = super(Concatenation, cls).__new__(cls)
            instance.children = children
            return instance

    is_atomic = False

    @property
    def accepting(self):
        return all(child.accepting for child in self.children)

    def derivative(self, char):
        """
        Build up a disjunction of derivatives, starting from the left, stopping
        when we hit a non-accepting regex.

        For example, consider the regex:
            a?[ab]?[abc]ad
        Its derivative with respect to "a" is:
            ([ab]?[abc]ad)|([abc]ad)|ad

        * The first disjunct is where the character is consumed by the first child.
        * The second is where the first child matched with ε, then the second child
          consumed the character.
        * The third is where the first two children matched with ε, then the third
          child consumed the character. At this point, we can go no further, since
          the "a" _must_ have been consumed by the third child.
        """
        derivative = EMPTY
        for i, child in enumerate(self.children):
            derivative = derivative | (child.derivative(char) + Concatenation(*self.children[i+1:]))
            if not child.accepting:
                break
        return derivative

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    def __str__(self):
        return ''.join(map(parenthesize_str, self.children))

    def __repr__(self):
        return '+'.join(map(parenthesize_repr, self.children))


@six.python_2_unicode_compatible
class Intersection(RegularExpression):
    def __new__(cls, *children):
        flattened_children = set()
        for child in children:
            if isinstance(child, Intersection):
                flattened_children |= set(child.children)
            else:
                flattened_children.add(child)
        children = flattened_children
        if EMPTY in children:
            return EMPTY
        elif EPSILON in children:
            if all(child.accepting for child in children):
                return EPSILON
            else:
                return EMPTY

        # Normalize all the charsets and negated charsets into (at most) two.
        charsets = {c for c in children if isinstance(c, CharSet) and not c.negated}
        negated_charsets = {c for c in children if isinstance(c, CharSet) and c.negated}
        children  = (children - charsets) - negated_charsets
        if charsets:
            charset = CharSet(reduce(operator.and_, (set(c.chars) for c in charsets)))
        else:
            charset = None
        if negated_charsets:
            negated_charset = CharSet(
                reduce(operator.or_, (set(c.chars) for c in negated_charsets)),
                negated=True)
        else:
            negated_charset = None

        if charset and negated_charset:
            # If we have a charset and a negated charset, then compute their
            # intersection.
            chars = set(charset.chars) - set(negated_charset.chars)
            if not chars:  # The intersection is empty, so simplify to that.
                return EMPTY
            else:
                charset = CharSet(chars)
                negated_charset = None

        if charset:
            # Now restrict chars down to those which all the other conjuncts can
            # accept. These are exactly the chars recognized by this regex, so
            # just return the charset.
            chars = {
                char for char in charset.chars
                if all(child.derivative(char).accepting for child in children)
            }
            if not chars:
                return EMPTY
            else:
                return CharSet(chars)
        elif negated_charset:
            children.add(charset or negated_charset)

        if len(children) == 1:
            return children.pop()
        else:
            instance = super(Intersection, cls).__new__(cls)
            instance.children = tuple(sorted(children))
            return instance

    is_atomic = False

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    @property
    def accepting(self):
        return all(child.accepting for child in self.children)

    def derivative(self, char):
        return reduce(operator.and_, (child.derivative(char) for child in self.children))

    def __str__(self):
        return '∩'.join(map(parenthesize_str, self.children))

    def __repr__(self):
        return '&'.join(map(parenthesize_repr, self.children))


@six.python_2_unicode_compatible
class CharSet(RegularExpression):
    def __new__(cls, chars, negated=False):
        instance = super(CharSet, cls).__new__(cls)
        instance.chars = tuple(sorted(chars))
        instance.negated = negated
        return instance

    accepting = False
    is_atomic = True

    def derivative(self, char):
        if self.negated:
            return EMPTY if char in self.chars else EPSILON
        else:
            return EPSILON if char in self.chars else EMPTY

    @property
    def identity_tuple(self):
        return (CharSet.__name__, self.negated, self.chars)

    def __str__(self):
        if len(self.chars) == 1 and not self.negated:
            return six.text_type(self.chars[0])
        return '[%s%s]' % ('^' if self.negated else '', ''.join(self.chars))

    def __repr__(self):
        return 'CharSet(%r, negated=%r)' % (tuple(sorted(self.chars)), self.negated)


@six.python_2_unicode_compatible
class Union(RegularExpression):
    def __new__(cls, *children):
        flattened_children = set()
        for child in children:
            if isinstance(child, Union):
                flattened_children |= set(child.children)
            else:
                flattened_children.add(child)
        children = flattened_children
        if children == {EMPTY}:
            return EMPTY
        elif EMPTY in children:
            children.remove(EMPTY)

        char_literals = {
            child for child in children
            if (isinstance(child, CharSet) and not child.negated)}
        if char_literals:
            chars = {char for literal in char_literals for char in literal.chars}
            children = children - char_literals
            children.add(CharSet(chars))
        if len(children) == 1:
            return children.pop()

        instance = super(Union, cls).__new__(cls)
        instance.children = tuple(sorted(children))
        return instance

    is_atomic = False

    @property
    def accepting(self):
        return any(child.accepting for child in self.children)

    def derivative(self, char):
        return reduce(operator.or_, (child.derivative(char) for child in self.children))

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    def __str__(self):
        return '|'.join(map(parenthesize_str, self.children))

    def __repr__(self):
        return '|'.join(map(parenthesize_repr, self.children))


@six.python_2_unicode_compatible
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
            instance = super(Complement, cls).__new__(cls)
            instance.regex = regex
            return instance

    @property
    def is_atomic(self):
        return self.regex.is_atomic

    @property
    def accepting(self):
        return not self.regex.accepting

    def derivative(self, char):
        return ~self.regex.derivative(char)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '~%s' % parenthesize_str(self.regex)

    def __repr__(self):
        return '~%s' % parenthesize_repr(self.regex)


@six.python_2_unicode_compatible
class Star(RegularExpression):
    def __new__(cls, regex):
        if regex is EMPTY or regex is EPSILON:
            return regex
        instance = super(Star, cls).__new__(cls)
        instance.regex = regex
        return instance

    accepting = True

    def derivative(self, char):
        return self.regex.derivative(char) + self

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '%s*' % parenthesize_str(self.regex)

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
    set_char = ~"[^\\]]"
    set_items = (range / escaped_metachar / ~"[^\\]]" )+
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
        return char

    def visit_any(self, node, children):
        return DOT

    def visit_char(self, node, children):
        child, = children
        return CharSet([child])

    def visit_set_char(self, node, children):
        char = node.text
        return char

    def visit_range(self, node, children):
        start, dash, end = children
        return reduce(
            operator.or_,
            [CharSet([chr(i)]) for i in range(ord(start), ord(end) + 1)])

    def visit_set_items(self, node, children):
        items = [
            item if isinstance(item, RegularExpression) else CharSet([item])
            for item, in children]
        return reduce(operator.or_, items)

    def visit_positive_set(self, node, children):
        [lbrac, inner, rbrac] = children
        return inner

    def visit_negative_set(self, node, children):
        [lbrac, inner, rbrac] = children
        assert isinstance(inner, CharSet) and inner.negated is False
        return CharSet(inner.chars, negated=True)

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
        if max_repeat is None:
            # Open ended range, like /a{4,}/
            opt = Star(regex)
        else:
            opt = reduce(
                operator.or_,
                [regex * repeat for repeat in range(0, max_repeat - min_repeat + 1)])

        return repeated + opt

    def visit_optional(self, node, children):
        regex, question_mark = children
        return regex | EPSILON

    def generic_visit(self, node, children):
        return children or node.text

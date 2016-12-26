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
    def __add__(self, other):
        return Concatenation(self, other)

    def __and__(self, other):
        return Intersection(self, other)

    def __or__(self, other):
        return Union(self, other)

    def __invert__(self):
        return Complement(self)

    @abc.abstractproperty
    def accepting(self):
        """
        Whether an end-string is accepted with this regex.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def derivative(self, char):
        raise NotImplementedError

    def matches(self, string):
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
        if left > right:
            left, right = right, left
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

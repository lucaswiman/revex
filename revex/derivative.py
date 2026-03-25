"""
Regex implementation using the Brzozowski derivative.

Loosely inspired by David MacIver's implementation here:
http://www.drmaciver.com/2016/12/proving-or-refuting-regular-expression-equivalence/

See also https://en.wikipedia.org/wiki/Brzozowski_derivative
"""

import operator
import re
import string
from functools import reduce, total_ordering
from typing import Optional, Set, Sequence, Tuple

from revex.dfa import String, DFA
from .dfa import DEFAULT_ALPHABET


@total_ordering
class RegularExpression:
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

    def as_dfa(self, alphabet=DEFAULT_ALPHABET):
        # type: (Sequence[String]) -> DFA[RegularExpression]
        """
        Based of the construction here: https://drona.csa.iisc.ernet.in/~deepakd/fmcs-06/seminars/presentation.pdf  # noqa
        Nodes are named by the regular expression that, starting at that node,
        matches that regular expression. In particular, the "start" node is
        labeled with `regex`.
        """
        dfa = DFA(
            start=self,
            start_accepting=self.accepting,
            alphabet=alphabet,
        )
        nodes = {self}  # type: Set[RegularExpression]
        while nodes:
            node = nodes.pop()
            for char in alphabet:
                derivative = node.derivative(char)
                if not dfa.has_node(derivative):
                    nodes.add(derivative)
                    dfa.add_state(derivative, derivative.accepting)
                dfa.add_transition(node, derivative, char)
        return dfa

    def __add__(self, other):
        return Concatenation(self, other)

    def __and__(self, other):
        return Intersection(self, other)

    def __or__(self, other):
        return Union(self, other)

    def __invert__(self):
        return Complement(self)

    def __mul__(self, repeat):  # type: (int) -> RegularExpression
        return EPSILON if repeat == 0 else reduce(operator.add, [self] * repeat)

    __rmul__ = __mul__

    @property
    def accepting(self):  # type: () -> bool
        """
        Whether an end-string is accepted with this regex.
        """
        raise NotImplementedError

    @property
    def has_lookahead(self):  # type: () -> bool
        """
        Whether or not this regex has a lookahead assertion.
        """
        return False

    @property
    def has_lookbehind(self):  # type: () -> bool
        """
        Whether or not this regex has a lookbehind assertion.
        """
        return False

    def derivative(self, char):  # type: (String) -> RegularExpression
        raise NotImplementedError

    def match(self, string):  # type: (String) -> bool
        regex = self
        for i in range(len(string)):
            regex = regex.derivative(string[i:i+1])
        return regex.accepting

    @property
    def identity_tuple(self):
        return (type(self).__name__, )

    def __hash__(self):
        if not hasattr(self, '_hash'):
            self._hash = hash(self.identity_tuple)
        return self._hash

    def __eq__(self, other):
        return type(self) == type(other) and self.identity_tuple == other.identity_tuple

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if not isinstance(other, RegularExpression):  # pragma: no cover
            raise TypeError(type(other))
        return self.identity_tuple < other.identity_tuple


def parenthesize_str(regex):
    return str(regex) if regex.is_atomic else '(%s)' % regex


def parenthesize_repr(regex):
    return repr(regex) if regex.is_atomic else '(%r)' % regex


class _Empty(RegularExpression):
    def __new__(cls):
        try:
            return EMPTY
        except NameError:
            return super().__new__(cls)

    accepting = False

    def derivative(self, char):  # type: (String) -> RegularExpression
        return EMPTY

    def __str__(self):
        return '∅'

    def __repr__(self):
        return 'EMPTY'


EMPTY = _Empty()


class _Epsilon(RegularExpression):
    def __new__(cls):
        try:
            return EPSILON
        except NameError:
            return super().__new__(cls)

    accepting = True

    def derivative(self, char):  # type: (String) -> RegularExpression
        return EMPTY

    def __str__(self):
        return 'ε'

    def __repr__(self):
        return 'EPSILON'


EPSILON = _Epsilon()


class _Dot(RegularExpression):
    """
    Special expression for matching any character.
    """
    def __new__(cls):
        try:
            return DOT
        except NameError:
            return super().__new__(cls)

    accepting = False

    def derivative(self, char):  # type: (String) -> RegularExpression
        return EPSILON

    def __str__(self):
        return '.'

    def __repr__(self):
        return 'DOT'


DOT = _Dot()


class Concatenation(RegularExpression):
    children = None  # type: Tuple[RegularExpression, ...]

    def __new__(cls, *children):  # type: (*RegularExpression) -> RegularExpression
        flattened_children = []
        for child in children:
            if isinstance(child, Concatenation):
                for subchild in child.children:
                    flattened_children.append(subchild)
            else:
                flattened_children.append(child)
        children = tuple(flattened_children)
        if EMPTY in children:
            return EMPTY
        children = tuple(child for child in children if child is not EPSILON)
        children = LookBehind.collapse_concatenation(children)
        children = LookAhead.collapse_concatenation(children)

        if not children:
            return EPSILON
        elif len(children) == 1:
            return children[0]
        else:
            instance = super().__new__(cls)
            instance.children = children
            return instance

    is_atomic = False

    @property
    def has_lookahead(self):  # type: () -> bool
        return self.children[-1].has_lookahead

    @property
    def has_lookbehind(self):  # type: () -> bool
        return self.children[0].has_lookbehind

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


class Intersection(RegularExpression):
    children = None  # type: Tuple[RegularExpression, ...]

    def __new__(cls, *children_tuple):  # type: (*RegularExpression) -> RegularExpression
        children = set()  # type: Set[RegularExpression]
        for child in children_tuple:
            if isinstance(child, Intersection):
                children |= set(child.children)
            else:
                children.add(child)
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
        children = (children - charsets) - negated_charsets
        if charsets:
            charset = CharSet(reduce(operator.and_, (set(c.chars) for c in charsets)))  # type: Optional[CharSet]
        else:
            charset = None
        if negated_charsets:
            negated_charset = CharSet(
                reduce(operator.or_, (set(c.chars) for c in negated_charsets)),
                negated=True)  # type: Optional[CharSet]
        else:
            negated_charset = None

        if charset and negated_charset:
            # If we have a charset and a negated charset, then compute their
            # difference.
            chars = set(charset.chars) - set(negated_charset.chars)  # type: Set[String]
            if not chars:  # The intersection is empty, so simplify to that.
                return EMPTY
            else:
                charset = CharSet(chars)
                negated_charset = None

        if charset:
            # Now restrict chars down to those which all the other conjuncts can
            # accept. These are exactly the chars recognized by this regex, so
            # just return the charset.
            acceptable_chars = {
                char for char in charset.chars
                if all(child.derivative(char).accepting for child in children)
            }  # type: Set[String]
            if not acceptable_chars:
                return EMPTY
            else:
                return CharSet(acceptable_chars)
        elif negated_charset:
            children.add(charset or negated_charset)

        if len(children) == 1:
            return children.pop()
        else:
            instance = super().__new__(cls)
            instance.children = tuple(sorted(children))
            return instance

    is_atomic = False

    @property
    def has_lookahead(self):  # type: () -> bool
        return any(child.has_lookahead for child in self.children)

    @property
    def has_lookbehind(self):  # type: () -> bool
        return any(child.has_lookbehind for child in self.children)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    @property
    def accepting(self):
        return all(child.accepting for child in self.children)

    def derivative(self, char):  # type: (String) -> RegularExpression
        return reduce(operator.and_, (child.derivative(char) for child in self.children))

    def __str__(self):
        return '∩'.join(map(parenthesize_str, self.children))

    def __repr__(self):
        return '&'.join(map(parenthesize_repr, self.children))


class CharSet(RegularExpression):
    negated = None  # type: bool
    chars = None  # type: tuple

    def __new__(cls, chars, negated=False):
        instance = super().__new__(cls)
        instance.chars = tuple(sorted(chars))
        instance.negated = negated
        return instance

    accepting = False
    is_atomic = True

    def derivative(self, char):  # type: (String) -> RegularExpression
        if self.negated:
            return EMPTY if char in self.chars else EPSILON
        else:
            return EPSILON if char in self.chars else EMPTY

    @property
    def identity_tuple(self):
        return (CharSet.__name__, self.negated, self.chars)

    def __str__(self):
        if len(self.chars) == 1 and not self.negated:
            return str(self.chars[0])
        return '[%s%s]' % ('^' if self.negated else '', ''.join(self.chars))

    def __repr__(self):
        return 'CharSet(%r, negated=%r)' % (tuple(sorted(self.chars)), self.negated)


charclasses = {
    c: ''.join(filter(re.compile(r'\%s' % c).match, string.printable))
    for c in 'swd'
}


class CharClass(CharSet):
    def __new__(cls, char):
        negated = char.isupper()
        chars = charclasses[char.lower()]
        instance = super().__new__(cls, chars, negated)
        instance.charclass = char
        return instance

    @property
    def identity_tuple(self):
        return (CharClass.__name__, self.negated, self.charclass)

    def __str__(self):
        if len(self.chars) == 1 and not self.negated:
            return str(self.chars[0])
        return '\\%s' % self.charclass

    def __repr__(self):
        return 'CharClass(%r)' % self.charclass


class Union(RegularExpression):
    children = None  # type: Tuple[RegularExpression, ...]

    def __new__(cls, *children):  # type: (*RegularExpression) -> RegularExpression
        flattened_children = set()  # type: Set[RegularExpression]
        for child in children:
            if isinstance(child, Union):
                flattened_children |= set(child.children)
            else:
                flattened_children.add(child)
        if flattened_children == {EMPTY}:
            return EMPTY
        elif EMPTY in children:
            flattened_children.remove(EMPTY)

        char_literals = {
            child for child in flattened_children
            if (isinstance(child, CharSet) and not child.negated)}
        if char_literals:
            chars = {char for literal in char_literals for char in literal.chars}
            flattened_children = flattened_children - char_literals
            flattened_children.add(CharSet(chars))
        children = tuple(sorted(flattened_children))
        if len(children) == 1:
            return children[0]

        instance = super().__new__(cls)
        instance.children = children
        return instance

    is_atomic = False

    @property
    def has_lookahead(self):  # type: () -> bool
        return any(child.has_lookahead for child in self.children)

    @property
    def has_lookbehind(self):  # type: () -> bool
        return any(child.has_lookbehind for child in self.children)

    def __add__(self, other):
        lookaheads = tuple(r for r in self.children if r.has_lookahead)
        if lookaheads:
            non_lookaheads = tuple(r for r in self.children if not r.has_lookahead)
            return (
                Union(*(r + other for r in lookaheads)) |
                (Union(*non_lookaheads) + other))
        else:
            return Concatenation(self, other)

    @property
    def accepting(self):
        return any(child.accepting for child in self.children)

    def derivative(self, char):  # type: (String) -> RegularExpression
        return reduce(operator.or_, (child.derivative(char) for child in self.children))

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.children)

    def __str__(self):
        return '|'.join(map(parenthesize_str, self.children))

    def __repr__(self):
        return '|'.join(map(parenthesize_repr, self.children))


class Complement(RegularExpression):
    regex = None  # type: RegularExpression

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
            instance = super().__new__(cls)
            instance.regex = regex
            return instance

    @property
    def has_lookahead(self):  # type: () -> bool
        return self.regex.has_lookahead

    @property
    def has_lookbehind(self):  # type: () -> bool
        return self.regex.has_lookbehind

    @property
    def is_atomic(self):
        return self.regex.is_atomic

    @property
    def accepting(self):
        return not self.regex.accepting

    def derivative(self, char):  # type: (String) -> RegularExpression
        return ~self.regex.derivative(char)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '~%s' % parenthesize_str(self.regex)

    def __repr__(self):
        return '~%s' % parenthesize_repr(self.regex)


class Star(RegularExpression):
    regex = None  # type: RegularExpression

    def __new__(cls, regex):
        if regex is EMPTY or regex is EPSILON:
            return regex
        instance = super().__new__(cls)
        instance.regex = regex
        return instance

    accepting = True

    @property
    def has_lookahead(self):  # type: () -> bool
        return self.regex.has_lookahead

    @property
    def has_lookbehind(self):  # type: () -> bool
        return self.regex.has_lookbehind

    def derivative(self, char):  # type: (String) -> RegularExpression
        return self.regex.derivative(char) + self

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.regex)

    def __str__(self):
        return '%s*' % parenthesize_str(self.regex)

    def __repr__(self):
        return 'Star(%r)' % self.regex


WHATEVER = Star(DOT)


class LookAhead(RegularExpression):
    accepting = None  # type: bool
    lookaround_re = None  # type: RegularExpression
    suffix = None  # type: RegularExpression

    def __new__(cls, lookaround_re, suffix):
        instance = super().__new__(cls)

        accepting = lookaround_re.accepting and suffix.accepting
        if lookaround_re is EMPTY or suffix is EMPTY:
            # The lookahead condition has failed
            return EMPTY
        # Note that if ``suffix is EPSILON``, we could simplify to just EMPTY,
        # but we don't to allow composing at group boundaries. For example:
        # /(foo(?=bar)).*/ is parsed as /(foo + (?=bar)) + .*/
        # Clearly /foo(?=bar)/ never matches any string.

        instance.lookaround_re = lookaround_re
        instance.suffix = suffix
        instance.accepting = accepting
        return instance

    has_lookahead = True

    @classmethod
    def collapse_concatenation(cls, children):
        # type: (Tuple[RegularExpression, ...]) -> Tuple[RegularExpression, ...]
        """
        Collapses LookAhead assertions from the right.
        """
        if len(children) < 2 or isinstance(children[-1], LookAhead):
            return children
        for index, child in reversed(list(enumerate(children))):
            if isinstance(child, LookAhead):
                tail = Concatenation(*children[index + 1:])
                new_lookahead = LookAhead(
                    lookaround_re=child.lookaround_re,
                    suffix=child.suffix + tail)
                return children[:index] + (new_lookahead, )
        return children

    def derivative(self, char):
        look_der = self.lookaround_re.derivative(char)
        post_der = self.suffix.derivative(char)
        return LookAhead(look_der, post_der)

    def __repr__(self):
        return 'LookAhead(%r, %r)' % (self.lookaround_re, self.suffix)

    def __str__(self):
        return '(?=%s)%s' % (self.lookaround_re, self.suffix)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.lookaround_re, self.suffix)

    def __add__(self, other):
        return LookAhead(self.lookaround_re, self.suffix + other)


class LookBehind(RegularExpression):
    accepting = None  # type: bool
    lookaround_re = None  # type: RegularExpression
    prefix = None  # type: RegularExpression

    def __new__(cls, prefix, lookaround_re):
        instance = super().__new__(cls)

        accepting = prefix.accepting and lookaround_re.accepting
        if lookaround_re is EMPTY or prefix is EMPTY:
            # The lookbehind condition has failed
            return EMPTY

        instance.lookaround_re = lookaround_re
        instance.prefix = prefix
        instance.accepting = accepting
        return instance

    has_lookbehind = True

    @classmethod
    def collapse_concatenation(cls, children):
        # type: (Tuple[RegularExpression, ...]) -> Tuple[RegularExpression, ...]
        """
        Collapses LookBehind assertions from the left.
        """
        if len(children) < 2 or isinstance(children[0], LookBehind):
            return children
        for index, child in enumerate(children):
            if isinstance(child, LookBehind):
                head = Concatenation(*children[:index])
                new_lookbehind = LookBehind(
                    lookaround_re=child.lookaround_re,
                    prefix=head + child.prefix)  # type: RegularExpression
                return (new_lookbehind, ) + children[index + 1:]
        return children

    def derivative(self, char):
        return LookBehind(
            prefix=self.prefix.derivative(char),
            lookaround_re=self.lookaround_re.derivative(char),
        )

    def __repr__(self):
        return 'LookBehind(%r, %r)' % (self.prefix, self.lookaround_re, )

    def __str__(self):
        return '%s(?<=%s)' % (self.prefix, self.lookaround_re)

    @property
    def identity_tuple(self):
        return (type(self).__name__, self.prefix, self.lookaround_re)


class RegexVisitor:
    """
    Compatibility wrapper that provides the same parse() interface as the
    old parsimonious-based NodeVisitor.
    """
    def parse(self, regex):  # type: (String) -> RegularExpression
        from revex.regex_grammar import parse_pattern
        return parse_pattern(regex)
